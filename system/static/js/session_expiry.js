// Global handler: redirect to index when server returns 401 (session expired / unauthorized)
(function () {
    // Handle jQuery AJAX errors (many parts of the app use $.ajax)
    if (window.jQuery) {
        $(document).ajaxError(function (event, jqxhr, settings, thrownError) {
            try {
                if (jqxhr && jqxhr.status === 401) {
                    // Don't auto-redirect if the user is already on the login page
                    // or if the request was the login endpoint itself — let the
                    // local error handler display messages.
                    var onLoginPage = window.location.pathname === '/' || window.location.pathname.indexOf('/usuarios/login') !== -1;
                    var isLoginRequest = (settings && settings.url && settings.url.indexOf('/usuarios/login') !== -1);
                    if (onLoginPage || isLoginRequest) {
                        return; // allow local error handling to proceed
                    }
                    // For other endpoints, redirect to index so the UI reloads to login
                    window.location.href = '/';
                }
            } catch (e) { /* noop */ }
        });
    }

    // Monkey-patch fetch to detect 401 responses
    if (window.fetch) {
        const _fetch = window.fetch.bind(window);
        window.fetch = function () {
            return _fetch.apply(null, arguments).then(function (resp) {
                try {
                    if (resp && resp.status === 401) {
                        // If current page is login or the request was the login endpoint,
                        // don't redirect so the local handler can show messages.
                        var onLoginPage = window.location.pathname === '/' || window.location.pathname.indexOf('/usuarios/login') !== -1;
                        var isLoginRequest = (resp.url && resp.url.indexOf('/usuarios/login') !== -1);
                        if (onLoginPage || isLoginRequest) {
                            return Promise.reject(new Error('Unauthorized'));
                        }
                        window.location.href = '/';
                        return Promise.reject(new Error('Unauthorized'));
                    }
                } catch (e) { /* noop */ }
                return resp;
            }, function (err) {
                return Promise.reject(err);
            });
        };
    }
})();
