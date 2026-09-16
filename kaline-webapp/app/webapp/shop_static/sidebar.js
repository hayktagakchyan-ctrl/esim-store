(function () {
  document.addEventListener("DOMContentLoaded", function () {
    var shell = document.getElementById("app-shell");
    var openBtn = document.getElementById("sidebar-open");
    var openAccountBtn = document.getElementById("sidebar-open-account");
    var closeBtn = document.getElementById("sidebar-close");
    var backdrop = document.getElementById("sidebar-backdrop");
    var sidebar = document.getElementById("sidebar");

    function openSidebar() {
      shell.classList.add("sidebar-open");
    }
    function closeSidebar() {
      shell.classList.remove("sidebar-open");
    }

    if (openBtn) openBtn.addEventListener("click", openSidebar);
    if (openAccountBtn) openAccountBtn.addEventListener("click", openSidebar);
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

    // Клик по пункту поддержки (в сайдбаре и в верхней навигации) — отправляем
    // скрытую форму создания чата вместо перехода по "#".
    var supportForm = document.getElementById("start-support-form");
    [document.getElementById("support-nav-link"), document.getElementById("support-nav-link-top"), document.getElementById("order-help-link")].forEach(function (link) {
      if (link && supportForm) {
        link.addEventListener("click", function (e) {
          e.preventDefault();
          supportForm.submit();
        });
      }
    });

    // Показать/скрыть пароль — кнопка-глазок рядом с полем (регистрация, вход,
    // смена/сброс пароля). data-target — id поля, которое переключаем.
    document.querySelectorAll(".password-toggle").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var input = document.getElementById(btn.dataset.target);
        if (!input) return;
        var willShow = input.type === "password";
        input.type = willShow ? "text" : "password";
        btn.textContent = willShow ? "🙈" : "👁";
        btn.setAttribute("aria-label", willShow ? "Скрыть пароль" : "Показать пароль");
      });
    });
  });
})();
