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

function setTheme(theme) {
  if (theme === 'auto') {
    const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    document.body.setAttribute('data-bs-theme', systemTheme);
  } else {
    document.body.setAttribute('data-bs-theme', theme);
  }
}

const savedTheme = localStorage.getItem('theme') || 'light';
document.querySelector(`input[value="${savedTheme}"]`).checked = true;
setTheme(savedTheme);

document.querySelectorAll('input[name="theme"]').forEach(function (radio) {
  radio.addEventListener('change', function () {
    const selectedTheme = this.value;
    localStorage.setItem('theme', selectedTheme);
    setTheme(selectedTheme);
  });
});

window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () {
  if (localStorage.getItem('theme') === 'auto') {
    setTheme('auto');
  }
});
