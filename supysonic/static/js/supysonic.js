/*
 * This file is part of Supysonic.
 * Supysonic is a Python implementation of the Subsonic server API.
 *
 * Copyright (C) 2017-2024 Óscar García Amor
 *               2017-2024 Alban 'spl0k' Féron
 *
 * Distributed under terms of the GNU AGPLv3 license.
 */

const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]')
const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl))

document.querySelectorAll('.modal').forEach(function (modal) {
  modal.addEventListener('show.bs.modal', function (e) {
    var href = e.relatedTarget.getAttribute('data-href');
    var btnOk = modal.querySelector('.btn-ok');
    btnOk.setAttribute('href', href);
    btnOk.addEventListener('click', function () {
      var modalInstance = bootstrap.Modal.getInstance(modal);
      modalInstance.hide();
    }, { once: true });
  });
});
