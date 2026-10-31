document.addEventListener('DOMContentLoaded', function () {
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('sidebarBackdrop');
  const toggle = document.getElementById('sidebarToggle');

  function cerrarSidebar() {
    if (sidebar) sidebar.classList.remove('sidebar-open');
    if (backdrop) backdrop.classList.remove('show');
  }

  if (toggle) {
    toggle.addEventListener('click', function () {
      if (!sidebar) return;
      sidebar.classList.toggle('sidebar-open');
      if (backdrop) backdrop.classList.toggle('show');
    });
  }
  if (backdrop) backdrop.addEventListener('click', cerrarSidebar);

  // Cierra el menú móvil al navegar.
  document.querySelectorAll('.sidebar .nav-link').forEach(function (enlace) {
    enlace.addEventListener('click', function () {
      if (window.innerWidth < 992) cerrarSidebar();
    });
  });

  // Confirmación para formularios marcados con data-confirm.
  document.querySelectorAll('form[data-confirm]').forEach(function (formulario) {
    formulario.addEventListener('submit', function (evento) {
      if (!window.confirm(formulario.dataset.confirm)) {
        evento.preventDefault();
      }
    });
  });

  // Tooltips de Bootstrap.
  if (window.bootstrap) {
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (elemento) {
      new bootstrap.Tooltip(elemento);
    });
  }

  // Cierre automático de mensajes después de 6 segundos.
  document.querySelectorAll('.alert-auto').forEach(function (alerta) {
    setTimeout(function () {
      if (window.bootstrap) {
        bootstrap.Alert.getOrCreateInstance(alerta).close();
      }
    }, 6000);
  });
});
