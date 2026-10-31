/* Documentacion tecnica de Coffea IA -- comportamiento.
   Sin librerias externas. Mejora progresiva: si esto no corre, el CSS ya muestra
   todos los apartados seguidos (clase .no-js por defecto en <html>, quitada aqui). */
(function () {
  "use strict";

  var html = document.documentElement;
  html.classList.remove("no-js");
  html.classList.add("js");

  var apartados = Array.prototype.slice.call(document.querySelectorAll(".apartado"));
  var ordenIds = apartados.map(function (s) { return s.id; });
  var indiceActual = 0;
  var reducirMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function motionReducidoActivo() {
    return reducirMovimiento || html.getAttribute("data-motion") === "reduced";
  }

  /* ---------------- Tema claro/oscuro ---------------- */
  function aplicarTema(modo) {
    if (modo === "auto") { html.removeAttribute("data-theme"); }
    else { html.setAttribute("data-theme", modo); }
    try { localStorage.setItem("coffea-docs-tema", modo); } catch (e) {}
    document.querySelectorAll(".selector-tema button").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.dataset.tema === modo));
    });
  }
  document.querySelectorAll(".selector-tema button").forEach(function (b) {
    b.addEventListener("click", function () { aplicarTema(b.dataset.tema); });
  });
  (function initTema() {
    var guardado = null;
    try { guardado = localStorage.getItem("coffea-docs-tema"); } catch (e) {}
    aplicarTema(guardado || "auto");
  })();

  /* ---------------- Movimiento reducido: control manual (para pruebas) ---------------- */
  document.querySelectorAll(".selector-movimiento button").forEach(function (b) {
    b.addEventListener("click", function () {
      html.setAttribute("data-motion", b.dataset.motion);
      document.querySelectorAll(".selector-movimiento button").forEach(function (x) {
        x.setAttribute("aria-pressed", String(x === b));
      });
    });
  });

  /* ---------------- Drawer (menu lateral en movil/tablet) ---------------- */
  var barraLateral = document.querySelector(".barra-lateral");
  var fondoOscurecido = document.querySelector(".fondo-oscurecido");
  var botonAbrirMenu = document.querySelector(".abrir-menu");
  var botonCerrarMenu = document.querySelector(".cerrar-menu");

  function abrirDrawer() {
    barraLateral.classList.add("abierta");
    fondoOscurecido.classList.add("visible");
    barraLateral.removeAttribute("inert");
    if (botonAbrirMenu) botonAbrirMenu.setAttribute("aria-expanded", "true");
    var primerEnlace = barraLateral.querySelector("a, input, button");
    if (primerEnlace) primerEnlace.focus();
  }
  function cerrarDrawer() {
    barraLateral.classList.remove("abierta");
    fondoOscurecido.classList.remove("visible");
    if (botonAbrirMenu) { botonAbrirMenu.setAttribute("aria-expanded", "false"); botonAbrirMenu.focus(); }
  }
  function esModoEscritorio() { return window.matchMedia("(min-width: 1200px)").matches; }
  if (botonAbrirMenu) botonAbrirMenu.addEventListener("click", abrirDrawer);
  if (botonCerrarMenu) botonCerrarMenu.addEventListener("click", cerrarDrawer);
  if (fondoOscurecido) fondoOscurecido.addEventListener("click", cerrarDrawer);
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && barraLateral.classList.contains("abierta")) cerrarDrawer();
  });

  /* ---------------- Progreso de lectura + indicador "apartado X de N" ---------------- */
  var relleno = document.querySelector(".barra-progreso .relleno");
  var indicadorApartado = document.querySelector(".indicador-apartado");
  var contenedorIndicador = document.querySelector(".barra-progreso").parentElement;

  function actualizarProgreso() {
    var i = indiceActual + 1;
    var n = ordenIds.length;
    if (relleno) relleno.style.width = (i / n * 100).toFixed(1) + "%";
    if (indicadorApartado) indicadorApartado.textContent = "Apartado " + i + " de " + n;
  }

  /* ---------------- Indicador deslizante en el menu lateral ---------------- */
  var indicadorNav = document.querySelector(".indicador-activo-nav");
  function moverIndicadorNav(enlace) {
    if (!indicadorNav || !enlace) return;
    var li = enlace.closest("li");
    indicadorNav.style.transform = "translateY(" + li.offsetTop + "px)";
    indicadorNav.style.height = li.offsetHeight + "px";
  }

  /* ---------------- Anuncio a lectores de pantalla ---------------- */
  var anunciador = document.querySelector("[data-anunciador]");
  function anunciar(texto) { if (anunciador) anunciador.textContent = texto; }

  /* ---------------- Contadores animados (una sola vez) ---------------- */
  var contadoresAnimados = new WeakSet();
  function animarContador(el) {
    if (contadoresAnimados.has(el)) return;
    contadoresAnimados.add(el);
    var destino = parseInt(el.dataset.valor, 10) || 0;
    if (motionReducidoActivo()) { el.textContent = String(destino); return; }
    var inicio = null;
    var duracion = 900;
    function paso(ts) {
      if (inicio === null) inicio = ts;
      var progreso = Math.min(1, (ts - inicio) / duracion);
      var facilitado = 1 - Math.pow(1 - progreso, 3);
      el.textContent = String(Math.round(destino * facilitado));
      if (progreso < 1) requestAnimationFrame(paso);
      else el.textContent = String(destino);
    }
    requestAnimationFrame(paso);
  }
  if ("IntersectionObserver" in window) {
    var obsContadores = new IntersectionObserver(function (entradas) {
      entradas.forEach(function (en) { if (en.isIntersecting) animarContador(en.target); });
    }, { threshold: 0.6 });
    document.querySelectorAll(".contador .valor[data-valor]").forEach(function (el) { obsContadores.observe(el); });
  } else {
    document.querySelectorAll(".contador .valor[data-valor]").forEach(animarContador);
  }

  /* ---------------- Tablas: indicador de "hay mas contenido" al desplazar ---------------- */
  document.querySelectorAll(".tabla-contenedor").forEach(function (cont) {
    var scroller = cont.querySelector(".tabla-scroll");
    if (!scroller) return;
    function revisar() {
      var hayMas = scroller.scrollWidth - scroller.clientWidth - scroller.scrollLeft > 4;
      cont.classList.toggle("tiene-mas", hayMas);
    }
    revisar();
    scroller.addEventListener("scroll", revisar, { passive: true });
    window.addEventListener("resize", revisar);
  });

  /* ---------------- Bloques de codigo: boton copiar ---------------- */
  document.querySelectorAll(".bloque-codigo").forEach(function (bloque) {
    var boton = bloque.querySelector(".boton-copiar");
    var codigo = bloque.querySelector("pre");
    if (!boton || !codigo) return;
    boton.addEventListener("click", function () {
      var texto = codigo.textContent;
      var marcarCopiado = function () {
        var textoOriginal = boton.querySelector(".texto-copiar").textContent;
        boton.classList.add("copiado");
        boton.querySelector(".texto-copiar").textContent = "Copiado";
        setTimeout(function () {
          boton.classList.remove("copiado");
          boton.querySelector(".texto-copiar").textContent = textoOriginal;
        }, 1600);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(texto).then(marcarCopiado).catch(function () {});
      } else {
        var ta = document.createElement("textarea");
        ta.value = texto; ta.style.position = "fixed"; ta.style.opacity = "0";
        document.body.appendChild(ta); ta.select();
        try { document.execCommand("copy"); marcarCopiado(); } catch (e) {}
        document.body.removeChild(ta);
      }
    });
  });

  /* ---------------- Pestañas (modelos) ---------------- */
  document.querySelectorAll(".pestanas").forEach(function (grupo) {
    var botones = Array.prototype.slice.call(grupo.querySelectorAll(".tab-boton"));
    var paneles = grupo.querySelectorAll(".panel-tab");
    var indicador = grupo.querySelector(".indicador-tab");
    function activar(idx, moverFoco) {
      botones.forEach(function (b, i) {
        var sel = i === idx;
        b.setAttribute("aria-selected", String(sel));
        b.tabIndex = sel ? 0 : -1;
        paneles[i].classList.toggle("activo", sel);
        if (sel && moverFoco) b.focus();
      });
      var activo = botones[idx];
      if (indicador && activo) {
        indicador.style.width = activo.offsetWidth + "px";
        indicador.style.transform = "translateX(" + activo.offsetLeft + "px)";
      }
    }
    botones.forEach(function (b, i) {
      b.addEventListener("click", function () { activar(i, false); });
      b.addEventListener("keydown", function (e) {
        if (e.key === "ArrowRight") { activar((i + 1) % botones.length, true); e.preventDefault(); }
        if (e.key === "ArrowLeft") { activar((i - 1 + botones.length) % botones.length, true); e.preventDefault(); }
      });
    });
    activar(0, false);
    window.addEventListener("resize", function () { activar(botones.findIndex(function (b) { return b.getAttribute("aria-selected") === "true"; }), false); });
  });

  /* ---------------- Diagrama de arquitectura: dibujo + hover + click ---------------- */
  var diagrama = document.querySelector(".diagrama-svg");
  if (diagrama) {
    if ("IntersectionObserver" in window) {
      var obsDiagrama = new IntersectionObserver(function (entradas, obs) {
        entradas.forEach(function (en) {
          if (en.isIntersecting) { diagrama.classList.add("dibujado"); obs.disconnect(); }
        });
      }, { threshold: 0.3 });
      obsDiagrama.observe(diagrama);
    } else {
      diagrama.classList.add("dibujado");
    }
    diagrama.querySelectorAll(".grupo-nodo").forEach(function (nodo) {
      nodo.addEventListener("mouseenter", function () { diagrama.classList.add("hay-hover"); nodo.classList.add("resaltado"); });
      nodo.addEventListener("mouseleave", function () { diagrama.classList.remove("hay-hover"); nodo.classList.remove("resaltado"); });
      nodo.addEventListener("focus", function () { diagrama.classList.add("hay-hover"); nodo.classList.add("resaltado"); });
      nodo.addEventListener("blur", function () { diagrama.classList.remove("hay-hover"); nodo.classList.remove("resaltado"); });
      nodo.addEventListener("click", function () {
        var fn = nodo.getAttribute("data-funcion");
        if (!fn) return;
        irAApartado(indiceDeApartado("ref-funciones"), true);
        setTimeout(function () {
          var entrada = document.getElementById("fn-" + fn);
          if (entrada) {
            entrada.scrollIntoView({ behavior: motionReducidoActivo() ? "auto" : "smooth", block: "center" });
            entrada.classList.add("resaltada-temporal");
            setTimeout(function () { entrada.classList.remove("resaltada-temporal"); }, 1600);
          }
        }, motionReducidoActivo() ? 50 : 380);
      });
      nodo.setAttribute("tabindex", "0");
      nodo.setAttribute("role", "button");
    });
  }

  /* ---------------- Filtro de la referencia de funciones ---------------- */
  document.querySelectorAll(".chip-filtro").forEach(function (chip) {
    chip.addEventListener("click", function () {
      document.querySelectorAll(".chip-filtro").forEach(function (c) { c.setAttribute("aria-pressed", "false"); });
      chip.setAttribute("aria-pressed", "true");
      var filtro = chip.dataset.filtro;
      document.querySelectorAll(".funcion-entrada").forEach(function (f) {
        var mostrar = filtro === "todas" || (f.dataset.secciones || "").indexOf(filtro) !== -1 ||
          (filtro === "sin-doc" && f.dataset.sinDoc === "1");
        f.style.display = mostrar ? "" : "none";
      });
    });
  });

  /* =====================================================================
     NAVEGACION POR APARTADOS (modo panel con mejora progresiva)
     ===================================================================== */
  function indiceDeApartado(id) { return ordenIds.indexOf(id); }

  function actualizarNavLateral(idx) {
    document.querySelectorAll(".enlace-nav").forEach(function (a) {
      var activo = a.getAttribute("href") === "#" + ordenIds[idx];
      a.classList.toggle("activo", activo);
      a.setAttribute("aria-current", activo ? "true" : "false");
      if (activo) moverIndicadorNav(a);
    });
    document.querySelectorAll(".toc-lateral a").forEach(function (a) {
      a.classList.toggle("activo", a.getAttribute("href") === "#" + ordenIds[idx]);
    });
  }

  function actualizarBotonesAnteriorSiguiente(idx) {
    document.querySelectorAll("[data-boton-anterior]").forEach(function (b) { b.disabled = idx === 0; });
    document.querySelectorAll("[data-boton-siguiente]").forEach(function (b) { b.disabled = idx === ordenIds.length - 1; });
  }

  function prepararEscalonado(seccion) {
    seccion.querySelectorAll("table").forEach(function (t) { t.classList.remove("entrando"); void t.offsetWidth; t.classList.add("entrando"); });
  }

  function irAApartado(idx, esAdelante, actualizarHash) {
    if (idx < 0 || idx >= ordenIds.length || idx === indiceActual) return;
    var anterior = apartados[indiceActual];
    var siguiente = apartados[idx];
    var direccionAdelante = esAdelante === undefined ? idx > indiceActual : esAdelante;

    function conmutar() {
      anterior.classList.remove("activo", "saliendo-adelante", "saliendo-atras");
      siguiente.classList.add("activo");
      siguiente.classList.add(direccionAdelante ? "entrando-adelante" : "entrando-atras");
      indiceActual = idx;
      actualizarNavLateral(idx);
      actualizarBotonesAnteriorSiguiente(idx);
      actualizarProgreso();
      prepararEscalonado(siguiente);
      window.scrollTo(0, 0);
      siguiente.setAttribute("tabindex", "-1");
      siguiente.focus({ preventScroll: true });
      var h1 = siguiente.querySelector("h1");
      anunciar("Apartado: " + (h1 ? h1.textContent : siguiente.id));
      setTimeout(function () { siguiente.classList.remove("entrando-adelante", "entrando-atras"); }, 500);
      if (actualizarHash !== false) {
        history.pushState({ apartado: ordenIds[idx] }, "", "#" + ordenIds[idx]);
      }
    }

    if (motionReducidoActivo()) {
      conmutar();
      return;
    }

    if (document.startViewTransition) {
      anterior.style.setProperty("--vt-name", "apartado");
      document.startViewTransition(conmutar);
    } else {
      anterior.classList.add(direccionAdelante ? "saliendo-adelante" : "saliendo-atras");
      setTimeout(conmutar, 180);
    }
  }

  // Enlaces del menu lateral / TOC / diagrama
  document.querySelectorAll('a[href^="#"]').forEach(function (a) {
    a.addEventListener("click", function (e) {
      var id = a.getAttribute("href").slice(1);
      var idx = indiceDeApartado(id);
      if (idx === -1) return; // ancla que no es un apartado (ej. #fn-...)
      e.preventDefault();
      irAApartado(idx);
      if (barraLateral.classList.contains("abierta")) cerrarDrawer();
    });
  });

  // Botones anterior/siguiente (arriba de barra inferior y al pie de cada apartado)
  document.querySelectorAll("[data-boton-anterior]").forEach(function (b) {
    b.addEventListener("click", function () { irAApartado(indiceActual - 1, false); });
  });
  document.querySelectorAll("[data-boton-siguiente]").forEach(function (b) {
    b.addEventListener("click", function () { irAApartado(indiceActual + 1, true); });
  });

  // Flechas del teclado (si el foco no esta en un campo de texto)
  document.addEventListener("keydown", function (e) {
    var enCampo = /^(INPUT|TEXTAREA)$/.test(document.activeElement.tagName);
    if (enCampo) return;
    if (e.key === "ArrowRight") irAApartado(indiceActual + 1, true);
    if (e.key === "ArrowLeft") irAApartado(indiceActual - 1, false);
  });

  // Deslizar (touch) en movil
  (function habilitarSwipe() {
    var xInicio = null, yInicio = null;
    var area = document.querySelector(".contenido-principal");
    area.addEventListener("touchstart", function (e) {
      xInicio = e.touches[0].clientX; yInicio = e.touches[0].clientY;
    }, { passive: true });
    area.addEventListener("touchend", function (e) {
      if (xInicio === null) return;
      var dx = e.changedTouches[0].clientX - xInicio;
      var dy = e.changedTouches[0].clientY - yInicio;
      if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.5) {
        if (dx < 0) irAApartado(indiceActual + 1, true); else irAApartado(indiceActual - 1, false);
      }
      xInicio = null; yInicio = null;
    }, { passive: true });
  })();

  // Atras/adelante del navegador
  window.addEventListener("popstate", function () {
    var id = location.hash.slice(1) || ordenIds[0];
    var idx = indiceDeApartado(id);
    if (idx !== -1) irAApartado(idx, idx > indiceActual, false);
  });

  // Estado inicial segun el hash de la URL
  (function estadoInicial() {
    var idPedido = location.hash.slice(1);
    var idxInicial = idPedido ? indiceDeApartado(idPedido) : 0;
    if (idxInicial === -1) idxInicial = 0;
    apartados.forEach(function (s, i) { s.classList.toggle("activo", i === idxInicial); });
    indiceActual = idxInicial;
    actualizarNavLateral(idxInicial);
    actualizarBotonesAnteriorSiguiente(idxInicial);
    actualizarProgreso();
    prepararEscalonado(apartados[idxInicial]);
    if (diagrama && idxInicial === indiceDeApartado(diagrama.closest(".apartado").id)) {
      diagrama.classList.add("dibujado");
    }
  })();

  /* =====================================================================
     BUSCADOR (propio, indice generado en el momento sobre el DOM)
     ===================================================================== */
  var indiceBusqueda = apartados.map(function (s, i) {
    // Se excluye el pie "Anterior/Siguiente" del texto indexado: es navegacion, no
    // contenido, y "Siguiente" ya incluye el titulo del proximo apartado (falseaba resultados).
    var clon = s.cloneNode(true);
    var pie = clon.querySelector(".nav-apartado");
    if (pie) pie.remove();
    return { idx: i, id: s.id, titulo: (s.querySelector("h1") || {}).textContent || s.id, texto: clon.textContent.replace(/\s+/g, " ") };
  });
  var campoBusqueda = document.querySelector(".buscador input");
  var listaResultados = document.querySelector(".resultados-busqueda");

  function contexto(texto, pos, len) {
    var inicio = Math.max(0, pos - 40);
    var fin = Math.min(texto.length, pos + len + 40);
    return (inicio > 0 ? "…" : "") + texto.slice(inicio, fin) + (fin < texto.length ? "…" : "");
  }

  function buscar(consulta) {
    listaResultados.innerHTML = "";
    var q = consulta.trim().toLowerCase();
    if (q.length < 2) { listaResultados.classList.remove("visible"); return; }
    var resultados = [];
    indiceBusqueda.forEach(function (item) {
      var pos = item.texto.toLowerCase().indexOf(q);
      if (pos !== -1) resultados.push({ item: item, pos: pos });
    });
    listaResultados.classList.add("visible");
    if (!resultados.length) {
      listaResultados.innerHTML = '<div class="sin-resultados">Sin resultados para "' + consulta + '".</div>';
      return;
    }
    resultados.slice(0, 12).forEach(function (r) {
      var a = document.createElement("a");
      a.href = "#" + r.item.id;
      a.className = "resultado";
      var tit = document.createElement("div"); tit.className = "titulo-res"; tit.textContent = r.item.titulo;
      var ctx = document.createElement("div"); ctx.className = "contexto-res";
      var textoContexto = contexto(r.item.texto, r.pos, consulta.length);
      ctx.innerHTML = textoContexto.replace(new RegExp("(" + q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "ig"), "<mark>$1</mark>");
      a.appendChild(tit); a.appendChild(ctx);
      a.addEventListener("click", function (e) {
        e.preventDefault();
        irAApartado(r.item.idx);
        listaResultados.classList.remove("visible");
        campoBusqueda.value = "";
        resaltarEnApartado(apartados[r.item.idx], consulta);
      });
      listaResultados.appendChild(a);
    });
  }
  function resaltarEnApartado(seccion, consulta) {
    // Resalta la primera aparicion del texto buscado dentro del apartado activo,
    // sin contar el pie de navegacion Anterior/Siguiente (no es contenido real).
    var pie = seccion.querySelector(".nav-apartado");
    var caminador = document.createTreeWalker(seccion, NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) {
        return (pie && pie.contains(n)) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
      }
    });
    var nodo;
    var re = new RegExp(consulta.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i");
    while ((nodo = caminador.nextNode())) {
      var m = re.exec(nodo.nodeValue);
      if (m) {
        var span = document.createElement("mark");
        var despues = nodo.splitText(m.index);
        despues.nodeValue = despues.nodeValue.slice(m[0].length);
        span.textContent = m[0];
        nodo.parentNode.insertBefore(span, despues);
        setTimeout(function () { span.scrollIntoView({ behavior: "smooth", block: "center" }); }, 400);
        setTimeout(function () { span.outerHTML = span.innerHTML; }, 3000);
        break;
      }
    }
  }
  if (campoBusqueda) {
    campoBusqueda.addEventListener("input", function () { buscar(campoBusqueda.value); });
    campoBusqueda.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { listaResultados.classList.remove("visible"); campoBusqueda.blur(); }
    });
    document.addEventListener("click", function (e) {
      if (!e.target.closest(".buscador")) listaResultados.classList.remove("visible");
    });
  }

  /* ---------------- Mostrar indicador de apartado al desplazar (leve) ---------------- */
  var contBarra = document.querySelector(".barra-progreso");
  window.addEventListener("scroll", function () {
    contBarra.classList.add("mostrar-indicador");
    clearTimeout(window.__t_ind);
    window.__t_ind = setTimeout(function () { contBarra.classList.remove("mostrar-indicador"); }, 1500);
  }, { passive: true });
})();
