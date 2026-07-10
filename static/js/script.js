/* ═══════════════════════════════════════════════════════════════
   SPICE GARDEN - Main JavaScript
   ═══════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', function() {
    // ─── Navbar Scroll Effect ───
    const navbar = document.getElementById('navbar');
    if (navbar) {
        window.addEventListener('scroll', function() {
            if (window.scrollY > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        });
    }

    // ─── Hamburger Menu ───
    const hamburger = document.getElementById('hamburger');
    const navLinks = document.getElementById('navLinks');
    if (hamburger && navLinks) {
        hamburger.addEventListener('click', function() {
            hamburger.classList.toggle('active');
            navLinks.classList.toggle('open');
        });
        navLinks.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                hamburger.classList.remove('active');
                navLinks.classList.remove('open');
            });
        });
    }

    // ─── Flash Messages ───
    document.querySelectorAll('.flash-close').forEach(btn => {
        btn.addEventListener('click', function() {
            this.parentElement.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => this.parentElement.remove(), 300);
        });
    });
    document.querySelectorAll('.flash-message').forEach(msg => {
        setTimeout(() => {
            if (msg.parentElement) {
                msg.style.animation = 'slideOut 0.3s ease forwards';
                setTimeout(() => msg.remove(), 300);
            }
        }, 5000);
    });

    // ─── Scroll Animations (Intersection Observer) ───
    initScrollAnimations();

    // ─── Lazy Loading for Background Images ───
    initLazyBackgrounds();

    // ─── Back to Top Button ───
    initBackToTop();

    // ─── Review Carousel ───
    initReviewCarousel();

    // ─── Cart Count on Load ───
    updateCartCount();
});

// ═══════════════════════════════════════════════════════════════
// SCROLL ANIMATIONS
// ═══════════════════════════════════════════════════════════════

function initScrollAnimations() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.15,
        rootMargin: '0px 0px -50px 0px'
    });

    document.querySelectorAll('.animate-on-scroll, .animate-fade-in, .animate-slide-left, .animate-slide-right, .animate-scale, .animate-stagger').forEach(el => {
        observer.observe(el);
    });
}

// ═══════════════════════════════════════════════════════════════
// REVIEW CAROUSEL
// ═══════════════════════════════════════════════════════════════

let carouselInterval = null;

function initReviewCarousel() {
    const track = document.querySelector('.reviews-track');
    if (!track) return;

    const slides = track.querySelectorAll('.review-slide');
    if (slides.length < 2) {
        // Hide carousel controls
        const controls = document.querySelector('.carousel-controls');
        if (controls) controls.style.display = 'none';
        // Show all slides in a grid
        track.style.transform = 'none';
        track.style.gap = '20px';
        track.style.flexWrap = 'wrap';
        slides.forEach(s => { s.style.minWidth = ''; s.style.flex = '1 1 300px'; });
        return;
    }

    let currentIndex = 0;
    const dotsContainer = document.querySelector('.carousel-dots');
    const prevBtn = document.querySelector('.carousel-prev');
    const nextBtn = document.querySelector('.carousel-next');

    // Create dots
    if (dotsContainer) {
        const totalSlides = Math.ceil(slides.length / getSlidesPerView());
        for (let i = 0; i < totalSlides; i++) {
            const dot = document.createElement('button');
            dot.className = 'carousel-dot' + (i === 0 ? ' active' : '');
            dot.setAttribute('aria-label', `Go to slide ${i + 1}`);
            dot.addEventListener('click', () => goToSlide(i));
            dotsContainer.appendChild(dot);
        }
    }

    function getSlidesPerView() {
        if (window.innerWidth >= 992) return 3;
        if (window.innerWidth >= 768) return 2;
        return 1;
    }

    function goToSlide(index) {
        const perView = getSlidesPerView();
        const maxIndex = Math.ceil(slides.length / perView) - 1;
        currentIndex = Math.max(0, Math.min(index, maxIndex));
        const offset = -(currentIndex * (100 / perView));
        track.style.transform = `translateX(${offset}%)`;

        // Update dots
        if (dotsContainer) {
            dotsContainer.querySelectorAll('.carousel-dot').forEach((d, i) => {
                d.classList.toggle('active', i === currentIndex);
            });
        }
    }

    function nextSlide() { goToSlide(currentIndex + 1); }
    function prevSlide() { goToSlide(currentIndex - 1); }

    if (prevBtn) prevBtn.addEventListener('click', () => { prevSlide(); resetCarouselAuto(); });
    if (nextBtn) nextBtn.addEventListener('click', () => { nextSlide(); resetCarouselAuto(); });

    // Auto-play
    function startCarouselAuto() {
        if (carouselInterval) clearInterval(carouselInterval);
        carouselInterval = setInterval(nextSlide, 4000);
    }
    function resetCarouselAuto() {
        if (carouselInterval) {
            clearInterval(carouselInterval);
            startCarouselAuto();
        }
    }

    // Handle resize
    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => goToSlide(currentIndex), 200);
    });

    // Pause on hover
    track.addEventListener('mouseenter', () => {
        if (carouselInterval) clearInterval(carouselInterval);
    });
    track.addEventListener('mouseleave', startCarouselAuto);

    startCarouselAuto();
}

// ═══════════════════════════════════════════════════════════════
// LAZY LOADING FOR BACKGROUND IMAGES
// ═══════════════════════════════════════════════════════════════

function initLazyBackgrounds() {
    const lazyImages = document.querySelectorAll('[data-bg]');
    if (lazyImages.length === 0) return;

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const el = entry.target;
                const bgUrl = el.getAttribute('data-bg');
                if (bgUrl) {
                    // Preload the image
                    const img = new Image();
                    img.onload = () => {
                        el.style.backgroundImage = `url('${bgUrl}')`;
                        el.classList.add('loaded');
                    };
                    img.src = bgUrl;
                }
                observer.unobserve(el);
            }
        });
    }, { threshold: 0.1 });

    lazyImages.forEach(el => observer.observe(el));
}

// ═══════════════════════════════════════════════════════════════
// BACK TO TOP BUTTON
// ═══════════════════════════════════════════════════════════════

function initBackToTop() {
    const btn = document.getElementById('backToTop');
    if (!btn) return;

    window.addEventListener('scroll', () => {
        if (window.scrollY > 400) {
            btn.classList.add('visible');
        } else {
            btn.classList.remove('visible');
        }
    });

    btn.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
}

// ═══════════════════════════════════════════════════════════════
// CART FUNCTIONS
// ═══════════════════════════════════════════════════════════════

function updateCartCount() {
    fetch('/api/cart')
        .then(r => r.json())
        .then(data => {
            const countEl = document.getElementById('cartCount');
            if (countEl) countEl.textContent = data.cart_count || 0;
        })
        .catch(() => {});
}

function addToCart(itemId, quantity = 1) {
    const btn = event.target.closest('.add-to-cart-btn');
    if (btn) {
        btn.classList.add('added');
        btn.innerHTML = '<i class="fas fa-check"></i> Added!';
        setTimeout(() => {
            btn.classList.remove('added');
            btn.innerHTML = '<i class="fas fa-plus"></i> Add';
        }, 1500);
    }

    fetch('/api/cart/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_id: itemId, quantity: quantity, modifiers: [], special_instructions: '' })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            const countEl = document.getElementById('cartCount');
            if (countEl) {
                countEl.textContent = data.cart_count;
                countEl.style.transform = 'scale(1.3)';
                setTimeout(() => countEl.style.transform = 'scale(1)', 200);
            }
            showToast('Item added to cart!', 'success');
        }
    })
    .catch(err => showToast('Error adding to cart', 'error'));
}

function updateCartItem(itemId, quantity) {
    fetch('/api/cart/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_id: itemId, quantity: quantity })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            updateCartCount();
            if (typeof loadCart === 'function') loadCart();
        }
    });
}

function removeFromCart(itemId) {
    fetch('/api/cart/remove', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_id: itemId })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            updateCartCount();
            if (typeof loadCart === 'function') loadCart();
            showToast('Item removed from cart', 'info');
        }
    });
}

// ═══════════════════════════════════════════════════════════════
// ORDER TRACKING
// ═══════════════════════════════════════════════════════════════

function trackOrder(orderNumber) {
    if (!orderNumber) {
        showToast('Please enter an order number', 'error');
        return;
    }
    fetch(`/api/order/${orderNumber}`)
        .then(r => {
            if (!r.ok) throw new Error('Order not found');
            return r.json();
        })
        .then(data => { displayOrderStatus(data); })
        .catch(() => { showToast('Order not found. Please check your order number.', 'error'); });
}

function displayOrderStatus(order) {
    const container = document.getElementById('trackingResult');
    if (!container) return;

    let itemsHtml = order.items.map(i => {
        let mods = i.modifiers && i.modifiers.length ? ' <small style="color:var(--gray-500);">('+i.modifiers.join(', ')+')</small>' : '';
        return `<div class="order-item-row"><span>${i.item_name} x ${i.quantity}${mods}</span><span>Rs. ${(i.unit_price * i.quantity).toFixed(0)}</span></div>`;
    }).join('');

    let stepsHtml = order.status_history.map(s => `
        <div class="tracking-step ${s.completed ? 'completed' : ''} ${s.active ? 'active' : ''}">
            <div class="tracking-step-icon">
                <i class="fas ${s.completed ? 'fa-check' : s.active ? 'fa-spinner fa-spin' : 'fa-circle'}"></i>
            </div>
            <div class="tracking-step-label">${s.status}</div>
        </div>
    `).join('');

    container.innerHTML = `
        <div class="order-status-card">
            <div class="order-status-header">
                <h3>Order ${order.order_number}</h3>
                <span class="status-badge status-${order.status}">${order.status}</span>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:15px;margin-bottom:20px;">
                <div><p style="color:var(--gray-500);font-size:0.85rem;">Customer</p><p style="font-weight:600;">${order.customer_name}</p></div>
                <div><p style="color:var(--gray-500);font-size:0.85rem;">Order Date</p><p style="font-weight:600;">${order.order_date}</p></div>
                <div><p style="color:var(--gray-500);font-size:0.85rem;">Order Type</p><p style="font-weight:600;text-transform:capitalize;">${order.order_type}</p></div>
                <div><p style="color:var(--gray-500);font-size:0.85rem;">Payment</p><p style="font-weight:600;text-transform:uppercase;">${order.payment_method}</p></div>
                ${order.discount_amount > 0 ? `<div><p style="color:var(--gray-500);font-size:0.85rem;">Discount</p><p style="font-weight:600;color:#2E7D32;">- Rs. ${order.discount_amount.toFixed(0)}</p></div>` : ''}
                ${order.tip_amount > 0 ? `<div><p style="color:var(--gray-500);font-size:0.85rem;">Tip</p><p style="font-weight:600;">Rs. ${order.tip_amount.toFixed(0)}</p></div>` : ''}
                <div><p style="color:var(--gray-500);font-size:0.85rem;">Total</p><p style="font-weight:700;color:var(--maroon);font-size:1.1rem;">Rs. ${order.total_amount.toFixed(0)}</p></div>
            </div>
            <div class="tracking-steps">${stepsHtml}</div>
            <div class="order-items-list">
                <h4 style="font-family:var(--font-heading);margin-bottom:10px;">Order Items</h4>
                ${itemsHtml}
            </div>
            <div style="margin-top:20px;text-align:center;">
                <button onclick="reorder('${order.order_number}')" class="btn btn-primary"><i class="fas fa-redo"></i> Reorder</button>
            </div>
        </div>`;
    container.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function reorder(orderNumber) {
    fetch(`/api/reorder/${orderNumber}`, { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                updateCartCount();
                showToast(data.message, 'success');
                setTimeout(() => window.location.href = '/cart', 1000);
            }
        });
}

// ═══════════════════════════════════════════════════════════════
// REVIEW FORM
// ═══════════════════════════════════════════════════════════════

function submitReview(e) {
    e.preventDefault();
    const form = e.target;
    const name = form.querySelector('[name="name"]').value.trim();
    const comment = form.querySelector('[name="comment"]').value.trim();
    const ratingInput = form.querySelector('input[name="rating"]:checked');
    const rating = ratingInput ? parseInt(ratingInput.value) : 5;

    if (!name || !comment) { showToast('Please fill in all fields', 'error'); return; }

    fetch('/api/reviews', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, rating, comment })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            form.style.display = 'none';
            document.getElementById('reviewSuccess').classList.remove('hidden');
            showToast('Thank you for your review!', 'success');
        } else {
            showToast(data.error || 'Error submitting review', 'error');
        }
    })
    .catch(() => showToast('Error submitting review', 'error'));
}

// ═══════════════════════════════════════════════════════════════
// NEWSLETTER
// ═══════════════════════════════════════════════════════════════

function subscribeNewsletter() {
    const email = document.getElementById('newsletterEmail').value.trim();
    if (!email) { showToast('Please enter your email', 'error'); return; }

    fetch('/api/newsletter/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success || data.message) {
            showToast(data.message || 'Subscribed successfully!', 'success');
            document.getElementById('newsletterEmail').value = '';
        } else {
            showToast(data.error || 'Error subscribing', 'error');
        }
    })
    .catch(() => showToast('Error subscribing', 'error'));
}

// ═══════════════════════════════════════════════════════════════
// TOAST NOTIFICATIONS
// ═══════════════════════════════════════════════════════════════

function showToast(message, type = 'info') {
    const container = document.querySelector('.flash-container') || createFlashContainer();
    const toast = document.createElement('div');
    toast.className = `flash-message flash-${type}`;
    toast.innerHTML = `<span>${message}</span><button class="flash-close">&times;</button>`;
    container.appendChild(toast);
    toast.querySelector('.flash-close').addEventListener('click', () => {
        toast.style.animation = 'slideOut 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    });
    setTimeout(() => {
        if (toast.parentElement) {
            toast.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => toast.remove(), 300);
        }
    }, 3000);
}

function createFlashContainer() {
    const container = document.createElement('div');
    container.className = 'flash-container';
    document.body.appendChild(container);
    return container;
}
