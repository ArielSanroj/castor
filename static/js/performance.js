// Performance optimizations for Castor Elecciones
// Lazy loading, animations, and accessibility improvements

(function() {
    'use strict';

    // ====================
    // LAZY LOADING IMAGES
    // ====================
    function initLazyLoading() {
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        if (img.dataset.src) {
                            img.src = img.dataset.src;
                            img.classList.add('loaded');
                            observer.unobserve(img);
                        }
                    }
                });
            }, {
                rootMargin: '50px 0px',
                threshold: 0.01
            });

            document.querySelectorAll('img[loading="lazy"]').forEach(img => {
                imageObserver.observe(img);
            });
        }
    }

    // ====================
    // SCROLL ANIMATIONS
    // ====================
    function initScrollAnimations() {
        if ('IntersectionObserver' in window) {
            const observerOptions = {
                threshold: 0.1,
                rootMargin: '0px 0px -50px 0px'
            };

            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('visible');
                    }
                });
            }, observerOptions);

            document.querySelectorAll('.animate-on-scroll').forEach(el => {
                observer.observe(el);
            });
        } else {
            // Fallback: Show all elements immediately
            document.querySelectorAll('.animate-on-scroll').forEach(el => {
                el.classList.add('visible');
            });
        }
    }

    // ====================
    // MODAL ACCESSIBILITY
    // ====================
    window.openDemoModal = function(interest) {
        const modal = document.getElementById('demoModal');
        if (!modal) return;

        // Pre-select interest if provided
        if (interest) {
            const interestMap = {
                'forecast': 'forecast',
                'campañas': 'campañas',
                'medios': 'medios'
            };
            const interestSelect = document.getElementById('demo-interest');
            if (interestSelect && interestMap[interest]) {
                interestSelect.value = interestMap[interest];
            }
        }

        modal.classList.add('show');
        modal.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
        
        // Trap focus in modal
        const focusableElements = modal.querySelectorAll(
            'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );
        
        if (focusableElements.length === 0) return;
        
        const firstFocusable = focusableElements[0];
        const lastFocusable = focusableElements[focusableElements.length - 1];
        
        // Focus first element
        setTimeout(() => firstFocusable.focus(), 100);
        
        // Handle keyboard navigation
        const handleKeyDown = function(e) {
            if (e.key === 'Escape') {
                closeDemoModal();
                return;
            }
            
            if (e.key === 'Tab') {
                if (e.shiftKey) {
                    if (document.activeElement === firstFocusable) {
                        e.preventDefault();
                        lastFocusable.focus();
                    }
                } else {
                    if (document.activeElement === lastFocusable) {
                        e.preventDefault();
                        firstFocusable.focus();
                    }
                }
            }
        };
        
        // Remove existing handler if any
        if (modal.dataset.keydownHandler === 'attached') {
            modal.removeEventListener('keydown', handleKeyDown);
        }
        
        modal.addEventListener('keydown', handleKeyDown);
        modal.dataset.keydownHandler = 'attached';
    };

    window.closeDemoModal = function() {
        const modal = document.getElementById('demoModal');
        if (!modal) return;

        modal.classList.remove('show');
        modal.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
        
        // Return focus to trigger element
        const openButton = document.querySelector('[onclick*="openDemoModal"]');
        if (openButton) {
            openButton.focus();
        }
    };

    // ====================
    // SMOOTH SCROLL
    // ====================
    function initSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                const href = this.getAttribute('href');
                if (href === '#') return;
                
                e.preventDefault();
                const target = document.querySelector(href);
                
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                    
                    // Update focus for accessibility
                    target.setAttribute('tabindex', '-1');
                    target.focus();
                }
            });
        });
    }

    // ====================
    // FORM VALIDATION
    // ====================
    function initFormValidation() {
        const form = document.getElementById('demoForm');
        if (!form) return;

        const inputs = form.querySelectorAll('input[required], select[required]');
        
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                validateField(this);
            });
            
            input.addEventListener('input', function() {
                if (this.classList.contains('error')) {
                    validateField(this);
                }
            });
        });

        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            let isValid = true;
            inputs.forEach(input => {
                if (!validateField(input)) {
                    isValid = false;
                }
            });

            if (isValid) {
                await submitForm(form);
            }
        });
    }

    function validateField(field) {
        const value = field.value.trim();
        let isValid = true;
        let errorMessage = '';

        // Remove previous error
        const existingError = field.parentElement.querySelector('.field-error');
        if (existingError) {
            existingError.remove();
        }
        field.classList.remove('error');
        field.setAttribute('aria-invalid', 'false');

        // Check required
        if (field.hasAttribute('required') && !value) {
            isValid = false;
            errorMessage = 'Este campo es obligatorio';
        }

        // Check email
        if (field.type === 'email' && value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                isValid = false;
                errorMessage = 'Ingrese un correo electrónico válido';
            }
        }

        // Check phone
        if (field.type === 'tel' && value) {
            const phoneRegex = /^[\d\s\+\-\(\)]+$/;
            if (!phoneRegex.test(value) || value.replace(/\D/g, '').length < 10) {
                isValid = false;
                errorMessage = 'Ingrese un número de teléfono válido';
            }
        }

        if (!isValid) {
            field.classList.add('error');
            field.setAttribute('aria-invalid', 'true');
            
            const errorElement = document.createElement('span');
            errorElement.className = 'field-error';
            errorElement.textContent = errorMessage;
            errorElement.setAttribute('role', 'alert');
            field.parentElement.appendChild(errorElement);
        }

        return isValid;
    }

    async function submitForm(form) {
        const submitButton = form.querySelector('button[type="submit"]');
        const originalText = submitButton.textContent;
        
        submitButton.disabled = true;
        submitButton.innerHTML = '<span class="spinner"></span> Enviando...';

        try {
            const formData = new FormData(form);
            const data = {
                first_name: formData.get('first_name'),
                last_name: formData.get('last_name'),
                email: formData.get('email'),
                phone: formData.get('phone'),
                interest: formData.get('interest'),
                location: formData.get('location')
            };

            // Get API base URL
            const apiBaseUrl = window.API_BASE_URL || window.location.origin;
            const endpoint = `${apiBaseUrl}/api/demo-request`;

            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok && result.success) {
                showMessage('¡Solicitud enviada exitosamente! Nos pondremos en contacto pronto.', 'success');
                form.reset();
                setTimeout(() => closeDemoModal(), 2000);
            } else {
                const errorMsg = result.error || result.message || 'Error al enviar la solicitud';
                showMessage(`Error: ${errorMsg}`, 'error');
            }

        } catch (error) {
            console.error('Error submitting form:', error);
            showMessage('Hubo un error al enviar la solicitud. Por favor intente nuevamente.', 'error');
        } finally {
            submitButton.disabled = false;
            submitButton.textContent = originalText;
        }
    }

    function showMessage(message, type) {
        const existingMessage = document.querySelector('.form-message');
        if (existingMessage) {
            existingMessage.remove();
        }

        const messageEl = document.createElement('div');
        messageEl.className = `form-message ${type}`;
        messageEl.textContent = message;
        messageEl.setAttribute('role', type === 'error' ? 'alert' : 'status');

        const form = document.getElementById('demoForm');
        form.insertBefore(messageEl, form.firstChild);

        setTimeout(() => messageEl.remove(), 5000);
    }

    // ====================
    // PERFORMANCE MONITORING
    // ====================
    function logPerformanceMetrics() {
        if ('PerformanceObserver' in window) {
            // Largest Contentful Paint (LCP)
            const lcpObserver = new PerformanceObserver((list) => {
                const entries = list.getEntries();
                const lastEntry = entries[entries.length - 1];
                console.log('LCP:', lastEntry.renderTime || lastEntry.loadTime);
            });
            lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });

            // First Input Delay (FID)
            const fidObserver = new PerformanceObserver((list) => {
                list.getEntries().forEach(entry => {
                    console.log('FID:', entry.processingStart - entry.startTime);
                });
            });
            fidObserver.observe({ entryTypes: ['first-input'] });

            // Cumulative Layout Shift (CLS)
            let clsScore = 0;
            const clsObserver = new PerformanceObserver((list) => {
                list.getEntries().forEach(entry => {
                    if (!entry.hadRecentInput) {
                        clsScore += entry.value;
                        console.log('CLS:', clsScore);
                    }
                });
            });
            clsObserver.observe({ entryTypes: ['layout-shift'] });
        }
    }

    // ====================
    // INITIALIZATION
    // ====================
    document.addEventListener('DOMContentLoaded', () => {
        initLazyLoading();
        initScrollAnimations();
        initSmoothScroll();
        initFormValidation();
        
        // Only log metrics in development
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            logPerformanceMetrics();
        }

        // Close modal on background click
        const modal = document.getElementById('demoModal');
        if (modal) {
            modal.addEventListener('click', function(e) {
                if (e.target === this) {
                    closeDemoModal();
                }
            });
        }
    });

    // ====================
    // SERVICE WORKER REGISTRATION (Optional)
    // ====================
    if ('serviceWorker' in navigator && window.location.protocol === 'https:') {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('/sw.js').then(
                registration => console.log('SW registered:', registration),
                err => console.log('SW registration failed:', err)
            );
        });
    }

})();
