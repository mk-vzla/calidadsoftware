
document.addEventListener('DOMContentLoaded', function () {
	const modal = document.getElementById('agregarProductoModal');
	const nombre = document.getElementById('nombre');
	const form = document.getElementById('formAgregarProducto');
	const codigo = document.getElementById('codigo_producto');

	if (!modal) return;

	// Validación al enviar
	if (form) {
		form.addEventListener('submit', function (e) {
			if (!form.checkValidity()) {
				e.preventDefault();
				e.stopPropagation();
				form.classList.add('was-validated');
			}
		}, false);
	}

	// función que pide el siguiente código al servidor
	let pending = null;
	function requestNextCode(letter) {
		if (!letter) return;
		const addModalEl = document.getElementById('agregarProductoModal');
		const template = (addModalEl && addModalEl.dataset) ? addModalEl.dataset.nextCodeTemplate || '' : '';
		if (!template) return;
		const url = template.replace('X', encodeURIComponent(letter));
		fetch(url)
			.then(function (resp) {
				if (!resp.ok) throw new Error('request failed');
				return resp.json();
			})
			.then(function (data) {
				if (data && data.next_code && codigo) {
					codigo.value = data.next_code;
				}
			})
			.catch(function () {
				// ignore errors silently
			});
	}

	if (nombre) {
		nombre.addEventListener('input', function () {
			const v = nombre.value.trim();
			if (!v) return;
			const letter = v.charAt(0).toUpperCase();
			if (pending) clearTimeout(pending);
			pending = setTimeout(function () { requestNextCode(letter); }, 300);
		});
	}

	// Cuando el modal termine de abrirse, ponemos el foco en el campo nombre (si existe)
	if (modal) {
		modal.addEventListener('shown.bs.modal', function () {
		// Pequeño timeout para asegurar que el foco se aplica después del render
		if (nombre) {
			setTimeout(function () { nombre.focus(); }, 10);
		}
		// si ya hay nombre, solicitar código
		if (nombre && nombre.value.trim()) {
			const letter = nombre.value.trim().charAt(0).toUpperCase();
			requestNextCode(letter);
		}
		});
	}

	// Reemplazar comas por puntos en los precios (presentación de miles)
	(function () {
		var prices = document.querySelectorAll('.price');
		prices.forEach(function (el) {
			el.textContent = el.textContent.replace(/,/g, '.');
		});
	})();

    // Validar que cantidad sea 0 o mayor
    const cantidad = document.getElementById('cantidad');
    if (cantidad) {
        cantidad.addEventListener('input', function () {
            if (cantidad.value < 0) {
                cantidad.value = 0;
            }
        });
    }

	// Validar cantidad del modal de modificar y submit del formModificarProducto
	const modCantidadInput = document.getElementById('mod_cantidad');
	if (modCantidadInput) {
		modCantidadInput.addEventListener('input', function () {
			if (modCantidadInput.value < 0) modCantidadInput.value = 0;
		});
	}
	const modFormEl = document.getElementById('formModificarProducto');
	if (modFormEl) {
		modFormEl.addEventListener('submit', function (e) {
			if (!modFormEl.checkValidity()) {
				e.preventDefault();
				e.stopPropagation();
				modFormEl.classList.add('was-validated');
			}
		}, false);
	}

	// Manejo del modal de modificación: rellenar campos al pulsar botón editar
	var editButtons = document.querySelectorAll('.btn-edit-product');
	if (editButtons && editButtons.length) {
		editButtons.forEach(function (btn) {
			// Use pointerdown (fires before click and before Bootstrap's click handler)
			var fillHandler = function (e) {
				// Evitar ejecuciones simultáneas / duplicadas (p. ej. pointerdown + keydown)
				if (btn.dataset._filling === '1') return;
				btn.dataset._filling = '1';
				// Obtener datos del producto desde los data-attrs
				var id = btn.dataset.id;

				// Campos del modal modificar
				var modCodigo = document.getElementById('mod_codigo_producto');
				var modNombre = document.getElementById('mod_nombre');
				var modDescripcion = document.getElementById('mod_descripcion');
				var modCategoria = document.getElementById('mod_categoria');
				var modPrecio = document.getElementById('mod_precio');
				var modCantidad = document.getElementById('mod_cantidad');
				var modForm = document.getElementById('formModificarProducto');

				// Ajustar action del form para enviar al endpoint de actualización
				if (modForm) {
					modForm.action = '/core/producto/update/' + encodeURIComponent(id) + '/';
					modForm.classList.remove('was-validated');
				}

				// Intentar obtener datos reales desde el servidor (mejor que depender de data-attrs)
				if (id) {
					fetch('/core/producto/json/' + encodeURIComponent(id) + '/')
						.then(function (resp) {
							if (!resp.ok) throw new Error('No se pudo obtener producto');
							return resp.json();
						})
						.then(function (data) {
							if (!data) throw new Error('Respuesta vacía');
							if (modCodigo) modCodigo.value = data.codigo_producto || '';
							if (modNombre) modNombre.value = data.nombre || '';
							if (modDescripcion) modDescripcion.value = data.descripcion || '';
							if (modCategoria) modCategoria.value = data.categoria || '';
							if (modPrecio) modPrecio.value = data.precio != null ? data.precio : '';
							if (modCantidad) modCantidad.value = data.cantidad != null ? data.cantidad : '';
						})
						.catch(function () {
							// Fallback: usar data-attrs si la petición falla
							var codigo = btn.getAttribute('data-codigo') || '';
							var nombreVal = btn.getAttribute('data-nombre') || '';
							var descripcionVal = btn.getAttribute('data-descripcion') || '';
							var categoriaVal = btn.getAttribute('data-categoria') || '';
							var precioVal = btn.getAttribute('data-precio') || '';
							var cantidadVal = btn.getAttribute('data-cantidad') || '';
							if (modCodigo) modCodigo.value = codigo;
							if (modNombre) modNombre.value = nombreVal;
							if (modDescripcion) modDescripcion.value = descripcionVal;
							if (modCategoria) modCategoria.value = categoriaVal;
							if (modPrecio) modPrecio.value = precioVal;
							if (modCantidad) modCantidad.value = cantidadVal;
						})
						.finally(function () {
							// permitir nuevo llenado
							try { btn.dataset._filling = '0'; } catch (err) { /* noop */ }
						});
				}
				else {
					// si no hay id, liberar bandera inmediatamente
					try { btn.dataset._filling = '0'; } catch (err) { /* noop */ }
				}
			};

			// Attach pointerdown for mouse/touch. Avoid duplicate fetches by
			// guarding with a dataset flag. We remove the mousedown fallback
			// because pointer events are supported in modern browsers and
			// caused duplicate requests in practice.
			btn.addEventListener('pointerdown', fillHandler);
			// Also handle keyboard activation (Enter/Space) via keydown
			btn.addEventListener('keydown', function (ev) {
				if (ev.key === 'Enter' || ev.key === ' ') {
					fillHandler(ev);
				}
			});
		}); // end editButtons.forEach
	} // end if (editButtons)

}); // end DOMContentLoaded