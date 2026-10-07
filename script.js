// Expose global methods for inline HTML calling (remove buttons)
window.appCart = [];

document.addEventListener("DOMContentLoaded", () => {
    // Intersection Observer
    const observer = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                obs.unobserve(entry.target);
            }
        });
    });
    document.querySelectorAll('.fade-in-up').forEach(el => observer.observe(el));

    // Smooth scroll
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if(href === '#' || href === '#cart' || href === '#login') return;
            const target = document.querySelector(href);
            if (target) {
                e.preventDefault();
                window.scrollTo({ top: target.offsetTop - 80, behavior: 'smooth' });
            }
        });
    });

    // CART SYSTEM
    window.appCart = JSON.parse(localStorage.getItem('naromyqa_cart')) || [];
    const FREE_SHIPPING_THRESHOLD = 80;
    
    // DARK MODE LOGIC
    const themeToggleBtn = document.querySelector('.theme-toggle-btn');
    
    // Initialize theme from local storage
    const currentTheme = localStorage.getItem('naromyqa_theme');
    if (currentTheme) {
        document.documentElement.setAttribute('data-theme', currentTheme);
    }
    
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            if (currentTheme === 'dark') {
                document.documentElement.removeAttribute('data-theme');
                localStorage.setItem('naromyqa_theme', 'light');
            } else {
                document.documentElement.setAttribute('data-theme', 'dark');
                localStorage.setItem('naromyqa_theme', 'dark');
            }
        });
    }
    
    // Protection XSS basique
    const escapeHTML = (str) => {
        if (!str) return '';
        return str.replace(/[&<>'"]/g, 
            tag => ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                "'": '&#39;',
                '"': '&quot;'
            }[tag] || tag)
        );
    };
    
    window.toggleCart = function(e) {
        if(e) e.preventDefault();
        const cartSidebar = document.getElementById('cart-sidebar');
        const cartOverlay = document.getElementById('cart-overlay');
        if(!cartSidebar) return;
        cartSidebar.classList.toggle('active');
        cartOverlay.classList.toggle('active');
        window.renderCart();
    }

    document.querySelectorAll('.cart-toggle').forEach(btn => btn.addEventListener('click', window.toggleCart));
    const closeBtn = document.getElementById('close-cart');
    const overlay = document.getElementById('cart-overlay');
    if(closeBtn) closeBtn.addEventListener('click', window.toggleCart);
    if(overlay) overlay.addEventListener('click', window.toggleCart);

    window.updateCartCount = function() {
        const totalItems = window.appCart.reduce((acc, item) => acc + item.quantity, 0);
        const countEl = document.getElementById('cart-count');
        if(countEl) countEl.textContent = totalItems;
    }

    window.updateCartStorage = function() {
        localStorage.setItem('naromyqa_cart', JSON.stringify(window.appCart));
        window.updateCartCount();
    }

    window.addToCartGlobal = function(name, price, image, quantity = 1) {
        const existing = window.appCart.find(i => i.name === name);
        if(existing) {
            existing.quantity += quantity;
        } else {
            window.appCart.push({ name, price, image, quantity });
        }
        window.updateCartStorage();
        window.renderCart();
        
        const cartSidebar = document.getElementById('cart-sidebar');
        if(cartSidebar && !cartSidebar.classList.contains('active')) {
            window.toggleCart();
        }
    }

    window.renderCart = function() {
        const cartItemsContainer = document.getElementById('cart-items');
        const cartTotalPrice = document.getElementById('cart-total-price');
        const shippingMsg = document.getElementById('shipping-message');
        const shippingFill = document.getElementById('shipping-progress-fill');
        
        if(!cartItemsContainer) return;
        cartItemsContainer.innerHTML = '';
        let total = 0;

        if (window.appCart.length === 0) {
            cartItemsContainer.innerHTML = `
                <div style="text-align:center; padding: 3rem 0;">
                    <p style="color:var(--text-secondary); margin-bottom: 1.5rem;">Votre panier est vide.</p>
                    <a href="boutique.html" class="btn-primary" style="padding:0.8rem 1.5rem;" onclick="window.toggleCart(); return false;">Continuer mes achats</a>
                </div>
            `;
            if(cartTotalPrice) cartTotalPrice.textContent = '0,00 €';
            if(shippingMsg) shippingMsg.innerHTML = `Livraison gratuite à partir de <strong>${FREE_SHIPPING_THRESHOLD} €</strong>`;
            if(shippingFill) shippingFill.style.width = '0%';
            return;
        }

        window.appCart.forEach((item, i) => {
            total += item.price * item.quantity;
            const div = document.createElement('div');
            div.className = 'cart-item';
            div.innerHTML = `
                <img src="${escapeHTML(item.image)}" alt="${escapeHTML(item.name)}">
                <div class="cart-item-details">
                    <div class="cart-item-title" style="font-weight:600;">${escapeHTML(item.name)}</div>
                    <div class="cart-item-price" style="margin-bottom:0.5rem;">${item.price.toFixed(2).replace('.', ',')} €</div>
                    <div class="cart-item-actions">
                        <button class="qty-btn" onclick="window.changeQty(${i}, -1)">-</button>
                        <span style="min-width:20px;text-align:center;">${item.quantity}</span>
                        <button class="qty-btn" onclick="window.changeQty(${i}, 1)">+</button>
                    </div>
                </div>
                <button class="remove-item" onclick="window.removeItem(${i})">&times;</button>
            `;
            cartItemsContainer.appendChild(div);
        });

        if(cartTotalPrice) cartTotalPrice.textContent = total.toFixed(2).replace('.', ',') + ' €';

        if(shippingMsg && shippingFill) {
            if(total >= FREE_SHIPPING_THRESHOLD) {
                shippingMsg.innerHTML = '🎉 <strong>Félicitations !</strong> Vous avez la livraison gratuite.';
                shippingFill.style.width = '100%';
                shippingFill.style.background = '#4CAF50';
            } else {
                const missing = (FREE_SHIPPING_THRESHOLD - total).toFixed(2).replace('.', ',');
                shippingMsg.innerHTML = `Plus que <strong>${missing} €</strong> pour la livraison offerte !`;
                shippingFill.style.width = ((total/FREE_SHIPPING_THRESHOLD)*100) + '%';
                shippingFill.style.background = 'var(--text-primary)';
            }
        }
    }

    window.changeQty = function(i, delta) {
        if(window.appCart[i].quantity + delta >= 1) {
            window.appCart[i].quantity += delta;
        } else if(delta < 0) {
            window.appCart.splice(i, 1);
        }
        window.updateCartStorage();
        window.renderCart();
    }
    
    window.removeItem = function(i) {
        window.appCart.splice(i, 1);
        window.updateCartStorage();
        window.renderCart();
    }

    // Bind boutique buttons
    document.querySelectorAll('.add-to-cart').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const card = e.target.closest('.product-card');
            const name = card.querySelector('h3').textContent;
            const price = 34.90;
            const image = card.querySelector('img').getAttribute('src');
            
            window.addToCartGlobal(name, price, image, 1);
            
            const orig = e.target.textContent;
            e.target.textContent = 'Ajouté ✓';
            e.target.style.background = '#4CAF50';
            e.target.style.borderColor = '#4CAF50';
            e.target.style.color = '#fff';
            setTimeout(() => {
                e.target.textContent = orig;
                e.target.style.background = '';
                e.target.style.borderColor = '';
                e.target.style.color = '';
            }, 1500);
        });
    });

    window.updateCartCount();
});
