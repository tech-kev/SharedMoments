// Translations: translationsArray is set inline in head.html, _() is defined in pwa.js

// Umschalten zwischen Modal anzeigen und verstecken
function callUi(id) {
   if (document.querySelector(id).classList.contains("active")) { // Wenn Modal angezeigt wird
      document.querySelector(id).classList.remove("active"); // Modal verstecken
      // Zugehäöriges Overlay verstecken
      if (id == "#dialog-nav-drawer") {
         document.getElementById("div-overlay-nav-drawer").classList.remove("active");
      } else if (id == "#dialog-manage-list-type") {
         document.getElementById("div-overlay-manage-list-type").classList.remove("active");
      } else if (id == "#dialog-edit-settings") {
         document.getElementById("div-overlay-settings").classList.remove("active");
      } else if (id == "#dialog-create-new-timeline-item") {
         document.getElementById("div-overlay-new-timeline-item").classList.remove("active");
      } else if (id == "#dialog-details-timeline-item") {
         document.getElementById("div-overlay-details-timeline-item").classList.remove("active");
      } else if (id == "#dialog-edit-timeline-item") {
         document.getElementById("div-overlay-edit-timeline-item").classList.remove("active");
      } else if (id == "#dialog-new-language") {
         document.getElementById("div-overlay-new-language").classList.remove("active");
      } else if (id == "#dialog-create-new-list-item") {
         document.getElementById("div-overlay-new-list-item").classList.remove("active");
      } else if (id == "#dialog-edition-confirm") {
         document.getElementById("div-overlay-edition-confirm").classList.remove("active");
      } else if (id == "#dialog-create-role") {
         document.getElementById("div-overlay-create-role").classList.remove("active");
      } else if (id == "#dialog-edit-user-roles") {
         document.getElementById("div-overlay-edit-user-roles").classList.remove("active");
      } else if (id == "#dialog-create-countdown") {
         document.getElementById("div-overlay-create-countdown").classList.remove("active");
      } else if (id == "#dialog-edit-countdown") {
         document.getElementById("div-overlay-edit-countdown").classList.remove("active");
      } else if (id == "#dialog-create-reminder") {
         document.getElementById("div-overlay-create-reminder").classList.remove("active");
      } else if (id == "#dialog-edit-reminder") {
         document.getElementById("div-overlay-edit-reminder").classList.remove("active");
      } else if (id == "#dialog-delete-ghostcard") {
         document.getElementById("div-overlay-delete-ghostcard").classList.remove("active");
      }
      document.body.style.overflow = "auto"; // Scrollen wieder erlauben
   } else {
      // Modal anzeigen
      document.querySelector(id).classList.add("active");
      // Zugehöriges Overlay anzeigen
      if (id == "#dialog-nav-drawer") {
         document.getElementById("div-overlay-nav-drawer").classList.add("active");
      } else if (id == "#dialog-manage-list-type") {
         document.getElementById("div-overlay-manage-list-type").classList.add("active");
      } else if (id == "#dialog-edit-settings") {
         document.getElementById("div-overlay-settings").classList.add("active");
      } else if (id == "#dialog-create-new-timeline-item") {
         document.getElementById("div-overlay-new-timeline-item").classList.add("active");
      } else if (id == "#dialog-details-timeline-item") {
         document.getElementById("div-overlay-details-timeline-item").classList.add("active");
      } else if (id == "#dialog-edit-timeline-item") {
         document.getElementById("div-overlay-edit-timeline-item").classList.add("active");
      } else if (id == "#dialog-new-language") {
         document.getElementById("div-overlay-new-language").classList.add("active");
      } else if (id == "#dialog-create-new-list-item") {
         document.getElementById("div-overlay-new-list-item").classList.add("active");
      } else if (id == "#dialog-edition-confirm") {
         document.getElementById("div-overlay-edition-confirm").classList.add("active");
      } else if (id == "#dialog-create-role") {
         document.getElementById("div-overlay-create-role").classList.add("active");
      } else if (id == "#dialog-edit-user-roles") {
         document.getElementById("div-overlay-edit-user-roles").classList.add("active");
      } else if (id == "#dialog-create-countdown") {
         document.getElementById("div-overlay-create-countdown").classList.add("active");
      } else if (id == "#dialog-edit-countdown") {
         document.getElementById("div-overlay-edit-countdown").classList.add("active");
      } else if (id == "#dialog-create-reminder") {
         document.getElementById("div-overlay-create-reminder").classList.add("active");
      } else if (id == "#dialog-edit-reminder") {
         document.getElementById("div-overlay-edit-reminder").classList.add("active");
      } else if (id == "#dialog-delete-ghostcard") {
         document.getElementById("div-overlay-delete-ghostcard").classList.add("active");
      }
      document.body.style.overflow = "hidden"; // Scrollen verhindern
   }
}

// Device Typ ermitteln
function getDeviceType() {
   const userAgent = navigator.userAgent;
   if (/Mobi/.test(userAgent) || /Android/i.test(userAgent)) {
       return 'mobile';
   } else {
       return 'desktop';
   }
}

function showSnackbar(element, isActive, type, message, data, moreInfo) {
   if (isActive === true) {
      document.getElementById(element+'-snackbar').classList.add('active', type);
      document.getElementById(element+'-snackbar-text').textContent = message;
   } else {
      document.getElementById(element+'-snackbar').classList.remove('active', type);
   }

   if (moreInfo === true) {
      document.getElementById(element+'-snackbar-more-link').textContent = "Details";
      document.getElementById(element+'-snackbar-more-link').addEventListener('click', () => {
         showMoreInfo(element, data, 'open');
      });
      document.getElementById(element+'-snackbar-more-link').addEventListener('click', () => {
      document.getElementById(element+'-snackbar').classList.remove('active', type);
      });
   } else {
      setTimeout(() => {
         document.getElementById(element+'-snackbar').classList.remove('active', type);
      }, 4000);
   }
}

function showSkeletonCards(containerId, count = 3) {
   const container = document.getElementById(containerId);
   if (!container) return;
   let html = '';
   for (let i = 0; i < count; i++) {
      html += `
         <article class="no-padding primary-container skeleton-card" style="margin-bottom: 1rem;">
            <div class="skeleton skeleton-image"></div>
            <div class="padding">
               <div class="skeleton skeleton-text medium"></div>
               <div class="skeleton skeleton-text long"></div>
               <div class="skeleton skeleton-text short"></div>
            </div>
         </article>
      `;
   }
   container.innerHTML = html;
}

// Button Loading State
function btnLoading(btn) {
   if (!btn || btn.disabled) return;
   btn.disabled = true;
   btn._originalHTML = btn.innerHTML;
   btn.innerHTML = '<progress class="circle small"></progress>';
}

function btnReset(btn) {
   if (!btn) return;
   btn.disabled = false;
   if (btn._originalHTML !== undefined) {
      btn.innerHTML = btn._originalHTML;
      delete btn._originalHTML;
   }
}

// Lazy Loading mit IntersectionObserver
const lazyObserver = new IntersectionObserver((entries) => {
   entries.forEach(entry => {
      if (entry.isIntersecting) {
         const img = entry.target;
         const realSrc = img.dataset.src;
         // Bild im Hintergrund vorladen, dann mit Fade einblenden
         const preload = new Image();
         preload.onload = () => {
            img.src = realSrc;
            img.classList.add('lazy-loaded');
            img.parentElement.classList.add('loaded');
         };
         preload.src = realSrc;
         lazyObserver.unobserve(img);
      }
   });
}, { rootMargin: '200px' });

function observeLazyImages(container) {
   const images = (container || document).querySelectorAll('img.lazy[data-src]');
   images.forEach(img => lazyObserver.observe(img));
}

document.addEventListener('DOMContentLoaded', () => {
   observeLazyImages();
   const btt = document.getElementById('btn-back-to-top');
   if (btt) {
      window.addEventListener('scroll', () => {
         const show = window.scrollY > 300;
         btt.style.opacity = show ? '1' : '0';
         btt.style.pointerEvents = show ? 'auto' : 'none';
      }, { passive: true });
   }
});

function showMoreInfo(element, result, mode) {
   if (mode === 'open') {
      document.body.style.overflow = "hidden";
      document.getElementById('div-overlay-'+element+'-error').classList.add('active');
      const detailEl = document.getElementById(element+'-error-more-details-text');
      detailEl.textContent = '';
      const code = document.createElement('p');
      code.textContent = `${_('Error code')}: ${result.data.error_code || '-'}`;
      const msg = document.createElement('p');
      msg.textContent = `${_('Error message')}: ${result.data.error_message || result.message || '-'}`;
      detailEl.appendChild(code);
      detailEl.appendChild(msg);
      document.getElementById(element+'-error-more-details').classList.add('active');
   } else if (mode === 'close') {
      document.getElementById('div-overlay-'+element+'-error').classList.remove('active');
      document.getElementById(element+'-error-more-details').classList.remove('active');
      document.body.style.overflow = "auto";
   }
}