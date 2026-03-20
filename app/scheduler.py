from datetime import date, timedelta, datetime
from config import Config
from app.logger import log
from app.db_queries import (
    get_all_reminders, get_setting_by_name, get_auto_reminder_by_source,
    create_reminder, update_reminder, delete_auto_reminders_by_source,
    check_notification_sent, log_notification, get_user_muted_reminder_ids,
    get_items_by_type, get_list_type_by_title, get_translation,
    get_user_setting, get_user_by_id
)
from app.models import SessionLocal, User, Reminder
from app.notifications import send_notification


def _t(key, lang):
    """Translate a key for a specific language."""
    return get_translation(key, lang)


def _get_user_lang(user_id):
    """Get the language setting for a user, defaulting to 'en'."""
    try:
        setting = get_user_setting(user_id, 'language')
        return setting.value if setting else 'en-US'
    except Exception:
        return 'en-US'

_scheduler = None

# Standard milestones in days
MILESTONE_DAYS = [100, 200, 365, 500, 730, 1000, 1095, 1500, 1825, 2000, 2500, 3650]
# Add full years up to 30 years
for y in range(11, 31):
    d = 365 * y
    if d not in MILESTONE_DAYS:
        MILESTONE_DAYS.append(d)
MILESTONE_DAYS.sort()


def start_scheduler(app):
    """Start the APScheduler background scheduler."""
    global _scheduler
    if _scheduler is not None:
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        _scheduler = BackgroundScheduler()

        # Check reminders every hour
        _scheduler.add_job(
            lambda: _run_with_app_context(app, check_reminders),
            'interval', hours=1, id='check_reminders',
            next_run_time=datetime.now() + timedelta(seconds=30)
        )

        # Sync auto-reminders daily at 2 AM
        _scheduler.add_job(
            lambda: _run_with_app_context(app, sync_auto_reminders),
            'cron', hour=2, minute=0, id='sync_auto_reminders'
        )

        # Also sync on startup after a short delay
        _scheduler.add_job(
            lambda: _run_with_app_context(app, sync_auto_reminders),
            'date', run_date=datetime.now() + timedelta(seconds=10),
            id='sync_auto_reminders_startup'
        )

        if app.config.get('DEMO_MODE'):
            from app.demo import cleanup_demo_sessions
            _scheduler.add_job(
                lambda: _run_with_app_context(app, cleanup_demo_sessions),
                'interval', minutes=Config.DEMO_SESSION_TIMEOUT, id='cleanup_demo_sessions'
            )

        _scheduler.start()
        log('info', 'Scheduler started')
    except ImportError:
        log('warning', 'APScheduler not installed, scheduler disabled')
    except Exception as e:
        log('error', f'Failed to start scheduler: {e}')


def _run_with_app_context(app, func):
    """Run a function within the Flask app context."""
    with app.app_context():
        try:
            func()
        except Exception as e:
            log('error', f'Scheduler job error in {func.__name__}: {e}')


def check_reminders():
    """Check all active reminders and send notifications where due."""
    setup = get_setting_by_name('setup_complete')
    if not setup or setup.value != 'True':
        return
    today = date.today()
    reminders = get_all_reminders()

    for reminder in reminders:
        try:
            _process_reminder(reminder, today)
        except Exception as e:
            log('error', f'Error processing reminder {reminder.id}: {e}')


def _process_reminder(reminder, today):
    """Process a single reminder: check dates and send notifications."""
    target_dates = _get_target_dates(reminder, today)
    if not target_dates:
        return

    notify_days = [int(d.strip()) for d in (reminder.notify_days_before or '0').split(',') if d.strip().isdigit()]

    for target_date in target_dates:
        for days_before in notify_days:
            notify_date = target_date - timedelta(days=days_before)
            if notify_date != today:
                continue

            notification_key = f'reminder_{reminder.id}_{today.isoformat()}_d{days_before}'
            if check_notification_sent(notification_key):
                continue

            _send_reminder_notifications(reminder, target_date, days_before)
            log_notification(notification_key, reminder.id)


def _get_target_dates(reminder, today):
    """Calculate the next relevant date(s) for a reminder."""
    dates = []

    if reminder.reminder_type == 'annual':
        if reminder.month and reminder.day:
            try:
                this_year = date(today.year, reminder.month, reminder.day)
                dates.append(this_year)
                # Also check next year (for notify_days_before crossing year boundary)
                next_year = date(today.year + 1, reminder.month, reminder.day)
                dates.append(next_year)
            except ValueError:
                pass

    elif reminder.reminder_type == 'one_time':
        if reminder.target_date:
            dates.append(reminder.target_date)

    elif reminder.reminder_type == 'milestone':
        if reminder.milestone_days:
            # Determine start date based on auto_source prefix
            if reminder.auto_source and reminder.auto_source.startswith('family_milestone_'):
                date_setting = get_setting_by_name('family_founding_date')
            elif reminder.auto_source and reminder.auto_source.startswith('friends_milestone_'):
                date_setting = get_setting_by_name('friend_group_founding_date')
            else:
                date_setting = get_setting_by_name('anniversary_date')
            if date_setting and date_setting.value:
                try:
                    start_date = datetime.strptime(date_setting.value, '%Y-%m-%d').date()
                    target = start_date + timedelta(days=reminder.milestone_days)
                    dates.append(target)
                except (ValueError, TypeError):
                    pass

    elif reminder.reminder_type == 'countdown':
        if reminder.countdown_id:
            from app.db_queries import get_item_by_id
            item = get_item_by_id(reminder.countdown_id)
            if item and item.dateCreated:
                countdown_date = item.dateCreated
                if hasattr(countdown_date, 'date'):
                    countdown_date = countdown_date.date()
                dates.append(countdown_date)

    return dates


def _send_reminder_notifications(reminder, target_date, days_before):
    """Send notification for a reminder to all non-muted users."""
    session = SessionLocal()
    try:
        users = session.query(User).filter(User.id != 1).all()
        user_ids = [u.id for u in users]
    finally:
        session.close()

    for user_id in user_ids:
        muted_ids = get_user_muted_reminder_ids(user_id)
        if reminder.id in muted_ids:
            continue

        lang = _get_user_lang(user_id)
        translated_title = _translate_reminder_title(reminder, lang)
        translated_desc = _translate_reminder_description(reminder, lang)

        if days_before == 0:
            title = translated_title
            body = translated_desc or _t('Today is {title}!', lang).format(title=translated_title)
        else:
            if days_before == 1:
                title = _t('{title} in 1 day', lang).format(title=translated_title)
            else:
                title = _t('{title} in {days} days', lang).format(title=translated_title, days=days_before)
            body = translated_desc or _t('{title} is on {date}', lang).format(
                title=translated_title, date=target_date.strftime('%d.%m.%Y'))

        send_notification(user_id, title, body)


def _translate_reminder_title(reminder, lang):
    """Translate a reminder title for a specific language."""
    if not reminder.is_auto:
        return reminder.title

    # Simple translatable keys
    if reminder.title in ('Anniversary', 'Wedding Day', 'Engagement Day', 'Family Day', 'Friendship Day'):
        return _t(reminder.title, lang)

    # Birthday pattern: "Birthday of <name>"
    if reminder.auto_source and reminder.auto_source.startswith('user_birthday_'):
        try:
            uid = int(reminder.auto_source.replace('user_birthday_', ''))
            user = get_user_by_id(uid)
            if user:
                return _t('Birthday of {name}', lang).format(name=user.firstName)
        except (ValueError, TypeError):
            pass
        return reminder.title

    # Milestone pattern (all prefixes)
    if reminder.auto_source and 'milestone_' in reminder.auto_source:
        days = reminder.milestone_days
        if days:
            if days % 365 == 0:
                return _t('{n}-Year Milestone', lang).format(n=days // 365)
            else:
                return _t('{n}-Day Milestone', lang).format(n=days)
        return reminder.title

    # Countdown pattern: "Countdown: <title>"
    if reminder.auto_source and reminder.auto_source.startswith('countdown_'):
        item_title = reminder.title
        if item_title.startswith('Countdown: '):
            item_title = item_title[len('Countdown: '):]
        return _t('Countdown: {title}', lang).format(title=item_title)

    return _t(reminder.title, lang)


def _translate_reminder_description(reminder, lang):
    """Translate a reminder description for a specific language."""
    if not reminder.is_auto or not reminder.description:
        return reminder.description

    if reminder.auto_source and 'milestone_' in reminder.auto_source:
        return ''

    # Countdown description
    if reminder.auto_source and reminder.auto_source.startswith('countdown_'):
        item_title = reminder.title
        if item_title.startswith('Countdown: '):
            item_title = item_title[len('Countdown: '):]
        return _t('Countdown "{title}" reached!', lang).format(title=item_title)

    return reminder.description


def sync_auto_reminders():
    """Sync auto-generated reminders from settings and user birthdays."""
    setup = get_setting_by_name('setup_complete')
    if not setup or setup.value != 'True':
        log('info', 'Skipping auto-reminder sync — setup not complete')
        return

    log('info', 'Syncing auto-reminders...')

    edition = get_setting_by_name('sm_edition').value

    # --- Couples-Reminder ---
    if edition == 'couples':
        date_settings = {
            'anniversary_date': 'Anniversary',
            'wedding_date': 'Wedding Day',
            'engaged_date': 'Engagement Day',
        }
        for setting_name, label in date_settings.items():
            setting = get_setting_by_name(setting_name)
            if setting and setting.value:
                try:
                    d = datetime.strptime(setting.value, '%Y-%m-%d').date()
                    _ensure_auto_annual_reminder(setting_name, label, d.month, d.day)
                    if setting_name == 'anniversary_date':
                        _ensure_milestone_reminders(d)
                except (ValueError, TypeError):
                    delete_auto_reminders_by_source(setting_name)
            else:
                delete_auto_reminders_by_source(setting_name)
    else:
        # Clean up Couples-Reminder when edition changed
        for source in ('anniversary_date', 'wedding_date', 'engaged_date'):
            delete_auto_reminders_by_source(source)
        _cleanup_milestones_by_prefix('milestone_')

    # --- Family-Reminder ---
    if edition == 'family':
        setting = get_setting_by_name('family_founding_date')
        if setting and setting.value:
            try:
                d = datetime.strptime(setting.value, '%Y-%m-%d').date()
                _ensure_auto_annual_reminder('family_founding_date', 'Family Day', d.month, d.day)
                _ensure_milestone_reminders(d, prefix='family_milestone_')
            except (ValueError, TypeError):
                delete_auto_reminders_by_source('family_founding_date')
                _cleanup_milestones_by_prefix('family_milestone_')
        else:
            delete_auto_reminders_by_source('family_founding_date')
            _cleanup_milestones_by_prefix('family_milestone_')
    else:
        delete_auto_reminders_by_source('family_founding_date')
        _cleanup_milestones_by_prefix('family_milestone_')

    # --- Friends-Reminder ---
    if edition == 'friends':
        setting = get_setting_by_name('friend_group_founding_date')
        if setting and setting.value:
            try:
                d = datetime.strptime(setting.value, '%Y-%m-%d').date()
                _ensure_auto_annual_reminder('friend_group_founding_date', 'Friendship Day', d.month, d.day)
                _ensure_milestone_reminders(d, prefix='friends_milestone_')
            except (ValueError, TypeError):
                delete_auto_reminders_by_source('friend_group_founding_date')
                _cleanup_milestones_by_prefix('friends_milestone_')
        else:
            delete_auto_reminders_by_source('friend_group_founding_date')
            _cleanup_milestones_by_prefix('friends_milestone_')
    else:
        delete_auto_reminders_by_source('friend_group_founding_date')
        _cleanup_milestones_by_prefix('friends_milestone_')

    # User birthdays
    session = SessionLocal()
    try:
        users = session.query(User).filter(User.id != 1, User.birthDate.isnot(None)).all()
        active_sources = set()
        for user in users:
            source = f'user_birthday_{user.id}'
            active_sources.add(source)
            label = f'Birthday of {user.firstName}'
            _ensure_auto_annual_reminder(source, label, user.birthDate.month, user.birthDate.day)
    finally:
        session.close()

    # Clean up birthday reminders for deleted users
    session = SessionLocal()
    try:
        auto_birthday_reminders = session.query(Reminder).filter(
            Reminder.is_auto == True, Reminder.auto_source.like('user_birthday_%')
        ).all()
        for r in auto_birthday_reminders:
            if r.auto_source not in active_sources:
                session.expunge(r)
                delete_auto_reminders_by_source(r.auto_source)
    finally:
        session.close()

    # Countdown integration
    _sync_countdown_reminders()

    log('info', 'Auto-reminder sync complete')


def _ensure_auto_annual_reminder(auto_source, title, month, day):
    """Create or update an auto-generated annual reminder."""
    existing = get_auto_reminder_by_source(auto_source)
    if existing:
        if existing.month != month or existing.day != day or existing.title != title:
            update_reminder(existing.id, title=title, month=month, day=day)
    else:
        create_reminder(
            title=title, description='', reminder_type='annual',
            created_by=1, month=month, day=day,
            notify_days_before='0,1,7', is_global=True,
            is_auto=True, auto_source=auto_source
        )


def _ensure_milestone_reminders(start_date, prefix='milestone_'):
    """Create milestone reminders for a given start date."""
    today = date.today()
    for days in MILESTONE_DAYS:
        target = start_date + timedelta(days=days)
        # Only create for future milestones (or within 30 days window)
        if target < today - timedelta(days=30):
            continue
        source = f'{prefix}{days}'
        if days % 365 == 0:
            label = f'{days // 365}-Year Milestone'
        else:
            label = f'{days}-Day Milestone'
        existing = get_auto_reminder_by_source(source)
        if not existing:
            create_reminder(
                title=label, description='',
                reminder_type='milestone', created_by=1,
                milestone_days=days, notify_days_before='0,1,7',
                is_global=True, is_auto=True, auto_source=source
            )
        elif existing.title != label:
            update_reminder(existing.id, title=label, description='')


def _cleanup_milestones_by_prefix(prefix):
    """Remove all milestone auto-reminders matching a prefix."""
    session = SessionLocal()
    try:
        reminders = session.query(Reminder).filter(
            Reminder.is_auto == True,
            Reminder.auto_source.like(f'{prefix}%')
        ).all()
        sources = [r.auto_source for r in reminders]
    finally:
        session.close()
    for source in sources:
        delete_auto_reminders_by_source(source)


def _sync_countdown_reminders():
    """Create auto-reminders for active countdowns."""
    countdown_lt = get_list_type_by_title('Countdown')
    if not countdown_lt:
        return

    items = get_items_by_type(countdown_lt.id, 'asc')
    active_sources = set()

    for row in items:
        # get_items_by_type returns Row(Item, User)
        item = row[0] if hasattr(row, '__getitem__') else row
        source = f'countdown_{item.id}'
        active_sources.add(source)

        if item.dateCreated:
            countdown_date = item.dateCreated
            if hasattr(countdown_date, 'date'):
                countdown_date = countdown_date.date()

            existing = get_auto_reminder_by_source(source)
            new_title = f'Countdown: {item.title}'
            new_desc = f'Countdown "{item.title}" reached!'
            if not existing:
                create_reminder(
                    title=new_title,
                    description=new_desc,
                    reminder_type='countdown', created_by=1,
                    countdown_id=item.id, notify_days_before='0',
                    is_global=True, is_auto=True, auto_source=source
                )
            elif existing.title != new_title or existing.description != new_desc:
                update_reminder(existing.id, title=new_title, description=new_desc)

    # Clean up countdown reminders for deleted items
    session = SessionLocal()
    try:
        auto_countdown_reminders = session.query(Reminder).filter(
            Reminder.is_auto == True, Reminder.auto_source.like('countdown_%')
        ).all()
        for r in auto_countdown_reminders:
            if r.auto_source not in active_sources:
                session.expunge(r)
                delete_auto_reminders_by_source(r.auto_source)
    finally:
        session.close()
