// Landing page enhancements for Castor Elecciones
(function() {
    'use strict';

    // ====================
    // MOBILE MENU
    // ====================
    function initMobileMenu() {
        const toggle = document.querySelector('.mobile-menu-toggle');
        const navCenter = document.querySelector('.nav-center');
        const navRight = document.querySelector('.nav-right');
        
        if (!toggle) return;

        // Create mobile menu container
        let mobileMenu = document.getElementById('mobile-menu');
        if (!mobileMenu) {
            mobileMenu = document.createElement('div');
            mobileMenu.id = 'mobile-menu';
            mobileMenu.className = 'mobile-menu';
            mobileMenu.setAttribute('aria-hidden', 'true');
            
            // Clone navigation links
            if (navCenter) {
                const centerClone = navCenter.cloneNode(true);
                centerClone.className = 'mobile-nav-center';
                mobileMenu.appendChild(centerClone);
            }
            
            if (navRight) {
                const rightClone = navRight.cloneNode(true);
                rightClone.className = 'mobile-nav-right';
                mobileMenu.appendChild(rightClone);
            }
            
            document.body.appendChild(mobileMenu);
        }

        toggle.addEventListener('click', function() {
            const isExpanded = toggle.getAttribute('aria-expanded') === 'true';
            
            toggle.setAttribute('aria-expanded', !isExpanded);
            mobileMenu.setAttribute('aria-hidden', isExpanded);
            mobileMenu.classList.toggle('active');
            document.body.style.overflow = isExpanded ? '' : 'hidden';
            
            // Animate hamburger icon
            toggle.classList.toggle('active');
        });

        // Close menu when clicking outside or on a link
        mobileMenu.addEventListener('click', function(e) {
            if (e.target.tagName === 'A') {
                toggle.setAttribute('aria-expanded', 'false');
                mobileMenu.setAttribute('aria-hidden', 'true');
                mobileMenu.classList.remove('active');
                document.body.style.overflow = '';
                toggle.classList.remove('active');
            }
        });
    }

    // ====================
    // STICKY HEADER EFFECT
    // ====================
    function initStickyHeader() {
        const header = document.querySelector('.main-header');
        if (!header) return;

        let lastScroll = 0;
        let ticking = false;

        function updateHeader() {
            const scrollY = window.scrollY;
            
            if (scrollY > 50) {
                header.classList.add('scrolled');
            } else {
                header.classList.remove('scrolled');
            }

            // Hide/show header on scroll
            if (scrollY > lastScroll && scrollY > 200) {
                header.classList.add('header-hidden');
            } else {
                header.classList.remove('header-hidden');
            }

            lastScroll = scrollY;
            ticking = false;
        }

        window.addEventListener('scroll', function() {
            if (!ticking) {
                window.requestAnimationFrame(updateHeader);
                ticking = true;
            }
        });
    }

    // ====================
    // SCROLL SPY NAVIGATION
    // ====================
    function initScrollSpy() {
        const navLinks = document.querySelectorAll('.nav-center a[href^="#"]');
        const sections = document.querySelectorAll('section[id]');
        
        if (!navLinks.length || !sections.length) return;

        const observerOptions = {
            rootMargin: '-20% 0px -70% 0px',
            threshold: 0
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const id = entry.target.getAttribute('id');
                    navLinks.forEach(link => {
                        link.classList.remove('active');
                        if (link.getAttribute('href') === `#${id}`) {
                            link.classList.add('active');
                        }
                    });
                }
            });
        }, observerOptions);

        sections.forEach(section => observer.observe(section));
    }

    // ====================
    // ENHANCED SMOOTH SCROLL
    // ====================
    function initEnhancedSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                const href = this.getAttribute('href');
                if (href === '#' || href === '#!') return;
                
                const target = document.querySelector(href);
                if (!target) return;
                
                e.preventDefault();
                
                const headerOffset = 80;
                const elementPosition = target.getBoundingClientRect().top;
                const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth'
                });

                // Update URL without jumping
                if (history.pushState) {
                    history.pushState(null, null, href);
                }
            });
        });
    }

    // ====================
    // PARALLAX EFFECT (Subtle)
    // ====================
    function initParallax() {
        const hero = document.querySelector('.hero');
        if (!hero) return;

        window.addEventListener('scroll', function() {
            const scrolled = window.pageYOffset;
            const rate = scrolled * 0.3;
            hero.style.transform = `translateY(${rate}px)`;
        });
    }

    // ====================
    // BUTTON HOVER EFFECTS
    // ====================
    function initButtonEffects() {
        const buttons = document.querySelectorAll('.primary-btn, .ghost-btn');
        
        buttons.forEach(button => {
            button.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-2px)';
            });
            
            button.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
            });
        });
    }

    // ====================
    // CARD HOVER EFFECTS
    // ====================
    function initCardEffects() {
        const cards = document.querySelectorAll('.product-card, .feature-card, .tech-card, .choice-card');
        
        cards.forEach(card => {
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-4px)';
            });
            
            card.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
            });
        });
    }

    // ====================
    // LAZY LOAD ANIMATIONS
    // ====================
    function initLazyAnimations() {
        if (!('IntersectionObserver' in window)) return;

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in');
                    observer.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        });

        document.querySelectorAll('.panel, section').forEach(section => {
            observer.observe(section);
        });
    }

    // ====================
    // BACK TO TOP BUTTON
    // ====================
    function initBackToTop() {
        const button = document.createElement('button');
        button.className = 'back-to-top';
        button.setAttribute('aria-label', 'Volver arriba');
        button.innerHTML = '↑';
        button.style.cssText = `
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            width: 48px;
            height: 48px;
            border-radius: 50%;
            background: var(--accent);
            color: white;
            border: none;
            cursor: pointer;
            opacity: 0;
            visibility: hidden;
            transition: all 0.3s ease;
            z-index: 1000;
            font-size: 1.5rem;
            box-shadow: 0 4px 12px rgba(255, 106, 61, 0.4);
        `;
        
        document.body.appendChild(button);

        window.addEventListener('scroll', function() {
            if (window.scrollY > 500) {
                button.style.opacity = '1';
                button.style.visibility = 'visible';
            } else {
                button.style.opacity = '0';
                button.style.visibility = 'hidden';
            }
        });

        button.addEventListener('click', function() {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }

    // ====================
    // VIDEO OVERLAY INTERACTION
    // ====================
    function initVideoOverlay() {
        const videoWrapper = document.querySelector('.video-wrapper');
        if (!videoWrapper) return;

        const overlay = videoWrapper.querySelector('.video-overlay');
        if (!overlay) return;

        // Prevent iframe from capturing clicks
        const iframe = videoWrapper.querySelector('iframe');
        if (iframe) {
            iframe.style.pointerEvents = 'none';
        }

        // Show overlay on hover
        videoWrapper.addEventListener('mouseenter', function() {
            overlay.style.opacity = '1';
            overlay.style.background = 'rgba(0,0,0,0.5)';
        });

        videoWrapper.addEventListener('mouseleave', function() {
            overlay.style.opacity = '0.7';
            overlay.style.background = 'rgba(0,0,0,0.3)';
        });

        // Ensure overlay is visible by default on mobile
        if (window.innerWidth <= 768) {
            overlay.style.opacity = '0.8';
        }

        // Handle click on overlay
        overlay.addEventListener('click', function(e) {
            e.stopPropagation();
            if (typeof window.openDemoModal === 'function') {
                window.openDemoModal();
            }
        });
    }

    // ====================
    // INITIALIZATION
    // ====================
    document.addEventListener('DOMContentLoaded', function() {
        initMobileMenu();
        initStickyHeader();
        initScrollSpy();
        initEnhancedSmoothScroll();
        initButtonEffects();
        initCardEffects();
        initLazyAnimations();
        initBackToTop();
        initVideoOverlay();
        
        // Only enable parallax on desktop
        if (window.innerWidth > 768) {
            initParallax();
        }
    });

})();


