(function () {
  function disableRevealReady() {
    document.documentElement.classList.remove("reveal-ready");
  }

  function ensureMeshBackground() {
    if (document.querySelector(".mesh-bg")) return;
    var mesh = document.createElement("div");
    mesh.className = "mesh-bg";
    document.body.prepend(mesh);
  }

  function setupScrollReveal() {
    try {
      // reveal-ready 由 base 模板 <head> 內聯腳本在「首次繪製前」加上，
      // 區塊一開始即為隱藏（從無到有）。若未加上（reduced-motion 或不支援
      // IntersectionObserver），代表內容保持可見，這裡不需處理。
      if (!document.documentElement.classList.contains("reveal-ready")) {
        return;
      }
      if (!("IntersectionObserver" in window)) {
        revealAll();
        return;
      }

      var targets = collectRevealTargets();
      if (!targets.length) {
        disableRevealReady();
        return;
      }

      var observer = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (!entry.isIntersecting) return;
            var el = entry.target;
            var idx = targets.indexOf(el);
            var delay = Math.min(idx, 6) * 70;
            el.style.transitionDelay = delay + "ms";
            el.classList.add("in-view");
            observer.unobserve(el);
          });
        },
        { threshold: 0.08, rootMargin: "0px 0px -8% 0px" }
      );

      targets.forEach(function (el) {
        observer.observe(el);
      });

      // 保險：5 秒後強制顯示，避免任何邊界情況導致內容隱形
      setTimeout(revealAll, 5000);
    } catch (err) {
      // 任何例外都不應讓頁面永久隱形，直接回退為可見。
      revealAll();
      disableRevealReady();
      console.error("[ui-fx] scroll reveal fallback:", err);
    }
  }

  function collectRevealTargets() {
    var targets = [];
    var pageContent = document.getElementById("pageContent");
    if (pageContent) {
      targets = Array.prototype.slice
        .call(pageContent.children)
        .filter(function (el) {
          return el.nodeType === 1 && typeof el.className === "string" && el.className.indexOf("col-") !== -1;
        });
    }
    return targets;
  }

  function revealAll() {
    collectRevealTargets().forEach(function (el) {
      el.classList.add("in-view");
    });
    disableRevealReady();
  }

  function bindQueryReadyPulse() {
    var input = document.getElementById("inputKeyword");
    if (!input) return;
    var cardBody = input.closest(".card-body");
    if (!cardBody) return;
    var buttons = cardBody.querySelectorAll(".btn-primary, .btn-success, .btn-accent");

    function sync() {
      var hasValue = input.value.trim().length > 0;
      buttons.forEach(function (btn) {
        btn.classList.toggle("btn-query-ready", hasValue);
      });
    }

    input.addEventListener("input", sync);
    input.addEventListener("keyup", sync);
    sync();
  }

  function init() {
    try {
      ensureMeshBackground();
      bindQueryReadyPulse();
      setupScrollReveal();
    } catch (err) {
      revealAll();
      disableRevealReady();
      console.error("[ui-fx] init fallback:", err);
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
