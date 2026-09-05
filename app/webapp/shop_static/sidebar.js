(function () {
  document.addEventListener("DOMContentLoaded", function () {
    var shell = document.getElementById("app-shell");
    var openBtn = document.getElementById("sidebar-open");
    var closeBtn = document.getElementById("sidebar-close");
    var backdrop = document.getElementById("sidebar-backdrop");
    var collapseBtn = document.getElementById("sidebar-collapse");
    var sidebar = document.getElementById("sidebar");

    function openSidebar() {
      shell.classList.add("sidebar-open");
    }
    function closeSidebar() {
      shell.classList.remove("sidebar-open");
    }

    if (openBtn) openBtn.addEventListener("click", openSidebar);
    if (closeBtn) closeBtn.addEventListener("click", closeSidebar);
    if (backdrop) backdrop.addEventListener("click", closeSidebar);
    if (sidebar) {
      sidebar.querySelectorAll(".nav-item").forEach(function (link) {
        link.addEventListener("click", closeSidebar);
      });
    }
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeSidebar();
    });

    // Свёрнутое состояние (иконки без подписей) — только для широких экранов, запоминаем выбор
    if (collapseBtn) {
      var collapsed = localStorage.getItem("sidebar_collapsed") === "1";
      if (collapsed) shell.classList.add("sidebar-collapsed");
      collapseBtn.addEventListener("click", function () {
        var isCollapsed = shell.classList.toggle("sidebar-collapsed");
        localStorage.setItem("sidebar_collapsed", isCollapsed ? "1" : "0");
      });
    }

    // Клик по пункту поддержки — отправляем скрытую форму создания чата
    var supportLink = document.getElementById("support-nav-link");
    var supportForm = document.getElementById("start-support-form");
    if (supportLink && supportForm) {
      supportLink.addEventListener("click", function (e) {
        e.preventDefault();
        supportForm.submit();
      });
    }
  });
})();
