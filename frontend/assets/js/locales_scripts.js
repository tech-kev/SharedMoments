/*
# Copyright (C) 2023 techkev
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
*/

let LCgalleryTitle
let LClocale
let LCcheckConsole
let LCloadFeedItemsError
let LCinvalidFiletype
let LCenterTitle
let LCenterFeedDesc
let LCeditModeOn
let LCeditMOdeOff
let LCwantDeleteEntry
let LCloadMusicSettingError
let LCloadSongError
let LCloadBucketlistError
let LCenterNameForEntry
let LCloadFilmlistError
let LCenterFilmname
let LCenterDate
let LCinvalidDate
let LCexample
let LCloadCountdownError
let LCsessionIDError
let LCnoPasswordEnterd
let LCloginFailed
let LCcheckServerlogs
let LCwrongPassword
let LCcheckSetupStateError
let LCloadMainTitleError
let LCloadAnniversaryDateError
let LCloadSpecialDayError
let LCloadDaysTogetherError
let LCloadBannerError
let LCloadMomentsError
let LCupdateMainTitleError
let LCupateAnniversaryDateError
let LCpasswordNoMatch
let LCnoNameOrBirthdaySet
let LCSetupFinishError
let LCsettingUpdateError
let LCloadBirthdayError
let LCloadRelationshipError
let LCcreateNewMoment
let LCimportSuccessful
let LCexportSuccessful
let LCwantImport
let LCimportFailed
let LCexportFailed
let LCwantExport
let LCenterMainTitle
let LCenterAnniversaryDate
let LCenterRelationship
let LCloadPushKeyError
let LCtestNotificationError

fetch(API_ENDPOINTS.locales, {
		method: 'GET'
	})
	.then(response => response.json())
	.then(data => {

		LCcheckConsole = data.check_console;
		LCloadFeedItemsError = data.LCloadFeedItemsError;
		LClocale = data.locale.replace("_", "-"); // Wandle den String de_DE in de-DE um, für toLocaleString
		LCgalleryTitle = data.gallery;
		LCinvalidFiletype = data.invalid_filetype;
		LCenterTitle = data.enter_title;
		LCenterFeedDesc = data.enter_desc_for_feed_entry;
		LCeditModeOn = data.edit_mode_on;
		LCeditMOdeOff = data.edit_mode_off;
		LCwantDeleteEntry = data.want_delete_entry;
		LCloadMusicSettingError = data.loading_music_setting_failed;
		LCloadSongError = data.loading_music_failed;
		LCloadBucketlistError = data.loadBucketlistError;
		LCenterNameForEntry = data.enter_name_for_entry;
		LCloadFilmlistError = data.loadFilmlistError;
		LCenterFilmname = data.enter_filmname;
		LCenterDate = data.enter_date;
		LCinvalidDate = data.invalid_date;
		LCexample = data.example;
		LCloadCountdownError = data.loadCountdownError;
		LCsessionIDError = data.session_id_error;
		LCnoPasswordEnterd = data.no_password_entered;
		LCloginFailed = data.login_failed;
		LCcheckServerlogs = data.check_serverlogs;
		LCwrongPassword = data.wrong_password;
		LCcheckSetupStateError = data.checkSetupStateError;
		LCloadMainTitleError = data.loadMainTitleError;
		LCloadAnniversaryDateError = data.loadAnniversaryDateError;
		LCloadSpecialDayError = data.loadSpecialDayError;
		LCloadDaysTogetherError = data.loadDaysTogetherError;
		LCloadBannerError = data.loadBannerError;
		LCloadMomentsError = data.loadMomentsError;
		LCupdateMainTitleError = data.updateMainTitleError;
		LCupateAnniversaryDateError = data.updateAnniversaryDateError;
		LCpasswordNoMatch = data.password_no_match;
		LCnoNameOrBirthdaySet = data.no_name_or_birthday_set;
		LCSetupFinishError = data.setup_finish_error;
		LCsettingUpdateError = data.setting_updated_failed;
		LCloadBirthdayError = data.loadBirthdayError;
		LCloadRelationshipError = data.loadRelationshipError;
		LCcreateNewMoment = data.create_new_moment;
		LCimportSuccessful = data.import_successful;
		LCexportSuccessful = data.export_successful;
		LCwantImport = data.want_import;
		LCimportFailed = data.import_failed;
		LCexportFailed = data.export_failed;
		LCwantExport = data.want_export;
		LCenterMainTitle = data.enterMainTitle;
		LCenterAnniversaryDate = data.enterAnniversaryDate;
		LCenterRelationship = data.enter_relationship;
		LCloadPushKeyError = data.load_push_key_error;
		LCtestNotificationError = data.test_Notification_Error;


	})
	.catch(error => {
		const errmessage = error + '! Please check the console!';
		callToast('error', errmessage);
		console.error(error);
	});


// Funktion hier, da in jedem Script nötig

function callToast(type, message) {
	var toastColor = 'red';
	if (type === 'info') {
		toastColor = 'green';
	}

	M.toast({
		html: '<strong>' + message + '</strong>',
		classes: 'rounded ' + toastColor
	});
}