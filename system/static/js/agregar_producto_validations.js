
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
		const template = modal.dataset.nextCodeTemplate || '';
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

	// Cuando el modal termine de abrirse, ponemos el foco en el campo nombre
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
});
