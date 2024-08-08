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

document.addEventListener('DOMContentLoaded', function () {

   fetch(API_ENDPOINTS.locales, {
         method: 'GET'
      })
      .then(response => response.json())
      .then(data => {

         if (window.location.pathname === "/") {

            document.getElementById('moments_title').textContent = data.moments_title;
            document.getElementById('countdownDays').textContent = data.countdown_days;
            document.getElementById('countdownHours').textContent = data.countdown_hours;
            document.getElementById('countdownMinutes').textContent = data.countdown_minutes;
            document.getElementById('countdownSeconds').textContent = data.countdown_seconds;
            document.getElementById('newFeedEntry').textContent = data.create_new_entry;
            document.getElementById('newFeedEntryTitle').textContent = data.title;
            document.getElementById('newFeedEntryDescription').textContent = data.description;
            document.getElementById('newFeedEntryDate').textContent = data.date_of_entry;
            document.getElementById('newFeedEntryFile').textContent = data.file;
            document.getElementById('newFeedEntryInputMedia').placeholder = data.picture_or_videos;
            document.getElementById('file-list-text').textContent = data.adapt_order_of_files_with_arrows;
            document.getElementById('newFeedEntryCancelButton').textContent = data.cancel;
            document.getElementById('newFeedEntrySaveButton').textContent = data.save;
            document.getElementById('updateFeedEntry').textContent = data.update_entry;
            document.getElementById('updateFeedEntryTitle').textContent = data.title;
            document.getElementById('updateFeedEntryDescription').textContent = data.description;
            document.getElementById('updateFeedEntryDate').textContent = data.date_of_entry;
            document.getElementById('updateFeedEntryFile').textContent = data.file;
            document.getElementById('updateFeedEntryInputMedia').placeholder = data.picture_or_videos;
            document.getElementById('update_file-list-text').textContent = data.adapt_order_of_files_with_arrows;
            document.getElementById('updateFeedEntryDeleteButton').textContent = data.delete;
            document.getElementById('updateFeedEntryCancelButton').textContent = data.cancel;
            document.getElementById('updateFeedEntrySaveButton').textContent = data.save;
            document.getElementById('newMomentsEntry').textContent = data.create_new_moment;
            document.getElementById('newMomentsEntryDescription').textContent = data.description;
            document.getElementById('newMomentsEntryDate').textContent = data.date;
            document.getElementById('newMomentsEntryCancelButton').textContent = data.cancel;
            document.getElementById('newMomentsEntrySaveButton').textContent = data.save;
            document.getElementById('updateMomentsEntry').textContent = data.update_moment;
            document.getElementById('updateMomentsEntryDescription').textContent = data.description;
            document.getElementById('updateMomentsEntryDate').textContent = data.date;
            document.getElementById('updateMomentsEntryDeleteButton').textContent = data.delete;
            document.getElementById('updateMomentsEntryCancelButton').textContent = data.cancel;
            document.getElementById('updateMomentsEntrySaveButton').textContent = data.save;
            document.getElementById('updateCountdownEntry').textContent = data.update_countdown;
            document.getElementById('updateCountdownEntryDescription').textContent = data.description;
            document.getElementById('updateCountdownEntryDate').textContent = data.date;
            document.getElementById('updateCountdownEntryCancelButton').textContent = data.cancel;
            document.getElementById('updateCountdownEntrySaveButton').textContent = data.save;

         } else if (window.location.pathname === "/bucketlist") {

            document.getElementById('bucketlistTitle').textContent = data.bucketlist_title;
            document.getElementById('add-btn').textContent = data.add;
            document.getElementById('newBucketlistEntryTitle').textContent = data.new_bucketlist_entry;
            document.getElementById('bucketlistTitleLabel').textContent = data.title;
            document.getElementById('cancelButton').textContent = data.cancel;
            document.getElementById('saveButton').textContent = data.save;

         } else if (window.location.pathname === "/filmlist") {

            document.getElementById('filmlistTitle').textContent = data.filmlist_title;
            document.getElementById('add-btn').textContent = data.add;
            document.getElementById('newFilmlistEntryTitle').textContent = data.new_filmlist_entry;
            document.getElementById('filmlistTitleLabel').textContent = data.movie_name;
            document.getElementById('cancelButton').textContent = data.cancel;
            document.getElementById('saveButton').textContent = data.save;

         } else if (window.location.pathname === "/galleryview") {

            document.getElementById('backButton').textContent = data.back;

         } else if (window.location.pathname === "/login") {

            document.getElementById('loginTitle').textContent = data.login;
            document.getElementById('enterPassword').textContent = data.enter_password + ":";
            document.getElementById('password-input').placeholder = data.password;
            document.getElementById('loginButton').textContent = data.login;

         } else if (window.location.pathname === "/settings") {

            document.title = "SharedMoments " + data.settings;
            document.getElementById('settingsTitle').textContent = data.change_settings;
            document.getElementById('settingsMenuTitle1').textContent = data.general;
            document.getElementById('settingsMenuTitle2').textContent = data.about_us;
            document.getElementById('settingsMenuTitle3').textContent = data.import_export;
            document.getElementById('settingsMenuTitle4').textContent = data.devtools;
            document.getElementById('settingsSubTitle1').textContent = data.settingsSubTitle1;
            document.getElementById('settingsSubText1').textContent = data.settingsSubText1;
            document.getElementById('settingsSubTitle2').textContent = data.settingsSubTitle2;
            document.getElementById('settingsSubText2').textContent = data.settingsSubText2;
            document.getElementById('settingsSubTitle3').textContent = data.settingsSubTitle3;
            document.getElementById('settingsSubText3').textContent = data.settingsSubText3;
            document.getElementById('settingsSubTitle4').textContent = data.settingsSubTitle4 + " ";
            document.getElementById('settingsSubText4').textContent = data.settingsSubText4;
            document.getElementById('settingsSubTitle5').textContent = data.settingsSubTitle4 + " ";
            document.getElementById('settingsSubText5').textContent = data.settingsSubText4;
            document.getElementById('settingsSubTitle6').textContent = data.settingsSubTitle6;
            document.getElementById('settingsSubText6').textContent = data.settingsSubText6;
            document.getElementById('settingsSub6Button').textContent = data.confirm;
            document.getElementById('settingsSubTitle7').textContent = data.settingsSubTitle7;
            document.getElementById('settingsSubText7').textContent = data.settingsSubText7;
            document.getElementById('settingsSub7Button').textContent = data.choose;
            document.getElementById('settingsSubTitle8').textContent = data.settingsSubTitle8;
            document.getElementById('settingsSubText8').textContent = data.settingsSubText8;
            document.getElementById('settingsSub8Button').textContent = data.choose;
            document.getElementById('settingsSubTitle9').textContent = data.settingsSubTitle9;
            document.getElementById('settingsSubText9').textContent = data.settingsSubText9;
            document.getElementById('settingsSubText10').textContent = data.settingsSubText10;
            document.getElementById('relationship_state1').textContent = data.relationship_state1;
            document.getElementById('relationship_state2').textContent = data.relationship_state2;
            document.getElementById('relationship_state3').textContent = data.relationship_state3;
            document.getElementById('relationship_state4').textContent = data.relationship_state4;
            document.getElementById('relationship_state1').value = data.relationship_state1;
            document.getElementById('relationship_state2').value = data.relationship_state2;
            document.getElementById('relationship_state3').value = data.relationship_state3;
            document.getElementById('relationship_state4').value = data.relationship_state4;
            document.getElementById('settingSubTitle12').textContent = data.settingSubTitle12;
            document.getElementById('settingSubText12').textContent = data.settingSubText12;
            document.getElementById('settingSubButton12').textContent = data.import;
            document.getElementById('settingSubTitle13').textContent = data.settingSubTitle13;
            document.getElementById('settingSubText13').textContent = data.settingSubText13;
            document.getElementById('settingSubButton13').textContent = data.export;
            document.getElementById('settingSubTitle14').textContent = data.notificationtest;
            document.getElementById('settingSubText14').textContent = data.settingSubText14;
            document.getElementById('settingSubButton14').textContent = data.push_me;
            document.getElementById('password').placeholder = data.password;
            document.getElementById('confirmPassword').placeholder = data.confirm_password;
            document.getElementById('settingsSubTitle11').textContent = data.settingsSubTitle11;
            document.getElementById('settingsSubText11').textContent = data.settingsSubText11;
            

         } else if (window.location.pathname === "/setup") {

            document.title = "SharedMoments " + data.setup;
            document.getElementById('setupTitle').textContent = data.setup;
            document.getElementById('setupMenuTitle1').textContent = data.general;
            document.getElementById('setupMenuTitle2').textContent = data.about_us;
            document.getElementById('setupMenuTitle3').textContent = data.only_import;
            document.getElementById('setupSubTitle1').textContent = data.settingsSubTitle1;
            document.getElementById('setupSubText1').textContent = data.settingsSubText1;
            document.getElementById('setupSubTitle2').textContent = data.settingsSubTitle2;
            document.getElementById('setupSubText2').textContent = data.setupSubText2;
            document.getElementById('setupSubText3').textContent = data.setupSubText3;
            document.getElementById('setupSubTitle3').textContent = data.settingsSubTitle3;
            document.getElementById('setupSubText4').textContent = data.settingsSubText3;
            document.getElementById('relationship_state1').textContent = data.relationship_state1;
            document.getElementById('relationship_state2').textContent = data.relationship_state2;
            document.getElementById('relationship_state3').textContent = data.relationship_state3;
            document.getElementById('relationship_state4').textContent = data.relationship_state4;
            document.getElementById('relationship_state1').value = data.relationship_state1;
            document.getElementById('relationship_state2').value = data.relationship_state2;
            document.getElementById('relationship_state3').value = data.relationship_state3;
            document.getElementById('relationship_state4').value = data.relationship_state4;
            document.getElementById('setupSubTitle4').textContent = data.setupSubTitle4 + " #1";
            document.getElementById('setupSubText5').textContent = data.setupSubText5;
            document.getElementById('setupNameOfPatner1').textContent = data.setupNameOfPatner1;
            document.getElementById('setupBirthdayOfPatner1').textContent = data.setupBirthdayOfPatner1;
            document.getElementById('setupSubTitle6').textContent = data.setupSubTitle4 + " #2";
            document.getElementById('setupSubText6').textContent = data.setupSubText6;
            document.getElementById('setupNameOfPatner2').textContent = data.setupNameOfPatner2;
            document.getElementById('setupBirthdayOfPatner2').textContent = data.setupBirthdayOfPatner2;
            document.getElementById('setupSubTitle7').textContent = data.setupSubTitle7;
            document.getElementById('setupSubText7').textContent = data.setupSubText7;
            document.getElementById('setupSubText8').textContent = data.setupSubText8;
            document.getElementById('password').placeholder = data.password;
            document.getElementById('confirmPassword').placeholder = data.confirm_password;
            document.getElementById('setupSubTitle9').textContent = data.setupSubTitle9;
            document.getElementById('setupSubText9').textContent = data.setupSubText9;
            document.getElementById('setupButtonChoose1').textContent = data.choose;
            document.getElementById('setupSubTitle10').textContent = data.setupSubTitle10;
            document.getElementById('setupSubText10').textContent = data.setupSubText10;
            document.getElementById('setupSubText11').textContent = data.setupSubText11;
            document.getElementById('setupButtonChoose2').textContent = data.choose;
            document.getElementById('setupButtonSave1').textContent = data.complete_setup;
            document.getElementById('settingSubTitle12').textContent = data.settingSubTitle12;
            document.getElementById('settingSubText12').textContent = data.settingSubText12;
            document.getElementById('settingSubButton12').textContent = data.import;
            document.getElementById('mainTitle').placeholder = data.our_moments;
            document.getElementById('nameUserA').placeholder = data.name;
            document.getElementById('nameUserB').placeholder = data.name;
            document.getElementById('settingsSubTitle11').textContent = data.settingsSubTitle11;
            document.getElementById('settingsSubText11').textContent = data.settingsSubText11;
         }

         if (window.location.pathname !== "/login" && window.location.pathname !== "/setup") { // Login + Setup hat kein Seitenmenü

            document.getElementById('sidemenuOverview').textContent = data.overview;
            document.getElementById('sidemenuHome').textContent = data.home;
            document.getElementById('sidemenuFilmlist').textContent = data.filmlist;
            document.getElementById('sidemenuBucketlist').textContent = data.bucketlist;
            document.getElementById('sidemenuSettings').textContent = data.settings;
            document.getElementById('sidemenuLogout').textContent = data.logout;
         }


      })
      .catch(error => {
         const errmessage = error + '! Please check the console!';
         callToast('error', errmessage);
         console.error(error);
      });
})