// SharedMoments — Reminders Page JS

let remindersData = [];

// ===== Initialization =====

document.addEventListener('DOMContentLoaded', () => {
   loadReminders();
});

// ===== Reminders CRUD =====

async function loadReminders() {
   try {
      const resp = await fetch('/api/v2/reminders');
      const result = await resp.json();
      if (result.status === 'success') {
         remindersData = result.data.reminders;
      }
   } catch (e) {
      console.error('Failed to load reminders:', e);
   }
}

function onReminderTypeChange(prefix) {
   const type = document.getElementById(prefix + '-reminder-type').value;
   document.getElementById(prefix + '-annual-fields').style.display = type === 'annual' ? '' : 'none';
   document.getElementById(prefix + '-onetime-fields').style.display = type === 'one_time' ? '' : 'none';
   document.getElementById(prefix + '-milestone-fields').style.display = type === 'milestone' ? '' : 'none';
}

function getNotifyDaysBefore(prefix) {
   const days = [];
   if (document.getElementById(prefix + '-notify-0')?.checked) days.push('0');
   if (document.getElementById(prefix + '-notify-1')?.checked) days.push('1');
   if (document.getElementById(prefix + '-notify-3')?.checked) days.push('3');
   if (document.getElementById(prefix + '-notify-7')?.checked) days.push('7');
   return days.join(',') || '0';
}

function setNotifyCheckboxes(prefix, notifyStr) {
   const days = (notifyStr || '0').split(',').map(d => d.trim());
   document.getElementById(prefix + '-notify-0').checked = days.includes('0');
   document.getElementById(prefix + '-notify-1').checked = days.includes('1');
   document.getElementById(prefix + '-notify-3').checked = days.includes('3');
   document.getElementById(prefix + '-notify-7').checked = days.includes('7');
}

async function saveReminder(btn) {
   const type = document.getElementById('create-reminder-type').value;
   const payload = {
      title: document.getElementById('create-reminder-title').value,
      description: document.getElementById('create-reminder-description').value,
      reminder_type: type,
      notify_days_before: getNotifyDaysBefore('create')
   };

   if (type === 'annual') {
      payload.month = parseInt(document.getElementById('create-reminder-month').value);
      payload.day = parseInt(document.getElementById('create-reminder-day').value);
   } else if (type === 'one_time') {
      payload.target_date = document.getElementById('create-reminder-target-date').value;
   } else if (type === 'milestone') {
      payload.milestone_days = parseInt(document.getElementById('create-reminder-milestone-days').value);
   }

   btnLoading(btn);

   try {
      const resp = await fetch('/api/v2/reminders', {
         method: 'POST',
         headers: { 'Content-Type': 'application/json' },
         body: JSON.stringify(payload)
      });
      const result = await resp.json();
      if (result.status === 'success') {
         btnReset(btn);
         callUi('#dialog-create-reminder');
         location.reload();
      } else {
         btnReset(btn);
         showSnackbar('reminders', true, 'error', result.message || _('An error occurred'), null, false);
      }
   } catch (e) {
      btnReset(btn);
      showSnackbar('reminders', true, 'error', _('An error occurred'), null, false);
   }
}

function openEditReminder(id) {
   const r = remindersData.find(r => r.id === id);
   if (!r) return;

   document.getElementById('edit-reminder-id').value = r.id;
   document.getElementById('edit-reminder-title').value = r.title;
   document.getElementById('edit-reminder-description').value = r.description || '';
   document.getElementById('edit-reminder-type').value = r.reminder_type;
   onReminderTypeChange('edit');

   if (r.reminder_type === 'annual') {
      document.getElementById('edit-reminder-month').value = r.month;
      document.getElementById('edit-reminder-day').value = r.day;
   } else if (r.reminder_type === 'one_time' && r.target_date) {
      document.getElementById('edit-reminder-target-date').value = r.target_date;
   } else if (r.reminder_type === 'milestone') {
      document.getElementById('edit-reminder-milestone-days').value = r.milestone_days;
   }

   setNotifyCheckboxes('edit', r.notify_days_before);
   callUi('#dialog-edit-reminder');
}

async function updateReminder(btn) {
   const id = document.getElementById('edit-reminder-id').value;
   const type = document.getElementById('edit-reminder-type').value;
   const payload = {
      title: document.getElementById('edit-reminder-title').value,
      description: document.getElementById('edit-reminder-description').value,
      reminder_type: type,
      notify_days_before: getNotifyDaysBefore('edit')
   };

   if (type === 'annual') {
      payload.month = parseInt(document.getElementById('edit-reminder-month').value);
      payload.day = parseInt(document.getElementById('edit-reminder-day').value);
   } else if (type === 'one_time') {
      payload.target_date = document.getElementById('edit-reminder-target-date').value;
   } else if (type === 'milestone') {
      payload.milestone_days = parseInt(document.getElementById('edit-reminder-milestone-days').value);
   }

   btnLoading(btn);

   try {
      const resp = await fetch(`/api/v2/reminders/${id}`, {
         method: 'PUT',
         headers: { 'Content-Type': 'application/json' },
         body: JSON.stringify(payload)
      });
      const result = await resp.json();
      if (result.status === 'success') {
         btnReset(btn);
         callUi('#dialog-edit-reminder');
         location.reload();
      } else {
         btnReset(btn);
         showSnackbar('reminders', true, 'error', result.message || _('An error occurred'), null, false);
      }
   } catch (e) {
      btnReset(btn);
      showSnackbar('reminders', true, 'error', _('An error occurred'), null, false);
   }
}

async function deleteReminder(id, btn) {
   if (!confirm(_('Delete this reminder?'))) return;
   btnLoading(btn);
   try {
      const resp = await fetch(`/api/v2/reminders/${id}`, { method: 'DELETE' });
      const result = await resp.json();
      if (result.status === 'success') {
         btnReset(btn);
         location.reload();
      } else {
         btnReset(btn);
         showSnackbar('reminders', true, 'error', result.message || _('An error occurred'), null, false);
      }
   } catch (e) {
      btnReset(btn);
      showSnackbar('reminders', true, 'error', _('An error occurred'), null, false);
   }
}

async function toggleMute(id, mute, btn) {
   btnLoading(btn);
   try {
      const resp = await fetch(`/api/v2/reminders/${id}/mute`, {
         method: mute ? 'POST' : 'DELETE'
      });
      const result = await resp.json();
      if (result.status === 'success') {
         btnReset(btn);
         location.reload();
      } else {
         btnReset(btn);
      }
   } catch (e) {
      btnReset(btn);
      showSnackbar('reminders', true, 'error', _('An error occurred'), null, false);
   }
}
