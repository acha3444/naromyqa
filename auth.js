// --- CONNEXION OFFICIELLE À SUPABASE ---
const SUPABASE_URL = 'https://vybyswxvllpflaktqdwg.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ5Ynlzd3h2bGxwZmxha3RxZHdnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTEzNzQ4NjUsImV4cCI6MjEwNjk1MDg2NX0.Lw7C6mIoizGW578qR19TmYokhYWHGplqKuxSShZIUgs'; 

let supabaseClient;
try {
    if (window.supabase) {
        supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
    }
} catch (e) {
    console.error("Erreur d'initialisation Supabase:", e);
}

// Fonction principale pour charger la logique
function initAuthLogic() {
    const authForm = document.getElementById('auth-form');
    const authBox = document.querySelector('.auth-box');
    const title = document.getElementById('auth-title');
    const subtitle = document.getElementById('auth-subtitle');
    const submitBtn = document.getElementById('auth-submit-btn');
    const switchTextNode = document.getElementById('auth-switch-text-node');
    const toggleAuth = document.getElementById('toggle-auth');
    const errorDiv = document.getElementById('auth-error');
    const successDiv = document.getElementById('auth-success');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    const firstnameInput = document.getElementById('firstname');
    const lastnameInput = document.getElementById('lastname');
    const signupOnlyFields = document.querySelector('.signup-only');

    let isLogin = true;

    function switchMode(forceToSignup = false) {
        if(!authBox) return;
        if(forceToSignup) {
            isLogin = false;
        } else {
            isLogin = !isLogin;
        }

        // Animation
        authBox.style.transform = 'scale(0.98)';
        authBox.style.opacity = '0.8';
        setTimeout(() => {
            authBox.style.transform = 'scale(1)';
            authBox.style.opacity = '1';
        }, 150);

        if(errorDiv) errorDiv.style.display = 'none';
        if(successDiv) successDiv.style.display = 'none';
        
        if(isLogin) {
            if(signupOnlyFields) signupOnlyFields.style.display = 'none';
            if(firstnameInput) firstnameInput.removeAttribute('required');
            if(lastnameInput) lastnameInput.removeAttribute('required');
            title.textContent = 'Bon retour';
            subtitle.textContent = 'Connectez-vous pour accéder à votre espace.';
            submitBtn.textContent = 'SE CONNECTER';
            switchTextNode.textContent = 'Pas encore de compte ? ';
            toggleAuth.textContent = 'Créer un compte';
        } else {
            if(signupOnlyFields) signupOnlyFields.style.display = 'block';
            if(firstnameInput) firstnameInput.setAttribute('required', 'true');
            if(lastnameInput) lastnameInput.setAttribute('required', 'true');
            title.textContent = 'Créer un compte';
            subtitle.textContent = 'Rejoignez Naromyqa en quelques secondes.';
            submitBtn.textContent = 'S\'INSCRIRE';
            switchTextNode.textContent = 'Déjà un compte ? ';
            toggleAuth.textContent = 'Se connecter';
        }
    }

    if(toggleAuth) {
        toggleAuth.addEventListener('click', (e) => {
            e.preventDefault();
            switchMode();
        });
    }

    if(authForm) {
        authForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            errorDiv.style.display = 'none';
            successDiv.style.display = 'none';

            if(!supabaseClient) {
                errorDiv.textContent = "Erreur: Le service de sécurité n'est pas chargé.";
                errorDiv.style.display = 'block';
                return;
            }

            const email = emailInput.value.trim();
            const password = passwordInput.value;

            submitBtn.classList.add('loading');
            const origText = submitBtn.textContent;
            submitBtn.textContent = 'Vérification...';

            try {
                if(isLogin) {
                    const { data, error } = await supabaseClient.auth.signInWithPassword({ email, password });
                    if (error) throw error;
                    
                    successDiv.textContent = "Connexion réussie ! Redirection...";
                    successDiv.style.display = 'block';
                    setTimeout(() => window.location.href = 'index.html', 800);
                } else {
                    const firstName = firstnameInput ? firstnameInput.value.trim() : '';
                    const lastName = lastnameInput ? lastnameInput.value.trim() : '';

                    const { data, error } = await supabaseClient.auth.signUp({ 
                        email, 
                        password,
                        options: {
                            data: {
                                first_name: firstName,
                                last_name: lastName
                            }
                        }
                    });
                    if (error) throw error;
                    
                    // Sécurité anti-doublon silencieux de Supabase
                    if (data.user && data.user.identities && data.user.identities.length === 0) {
                        errorDiv.textContent = "Ce compte existe déjà. Veuillez vous connecter.";
                        errorDiv.style.display = 'block';
                        setTimeout(() => switchMode(false), 2000);
                        return;
                    }
                    
                    // --- NOUVEAU : Alerter Klaviyo pour le mail de bienvenue ---
                    try {
                        await fetch('http://localhost:8083/welcome-event', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ email: email, first_name: firstName })
                        });
                    } catch (e) {
                        console.error("Impossible de notifier Klaviyo de la création de compte", e);
                    }
                    
                    successDiv.textContent = "Inscription réussie ! Connexion en cours...";
                    successDiv.style.display = 'block';
                    setTimeout(() => window.location.href = 'index.html', 1500);
                }
            } catch (error) {
                let msg = error.message || String(error);
                if(msg.includes('Invalid login credentials')) {
                    errorDiv.textContent = "Compte introuvable ou mot de passe incorrect. Redirection vers l'inscription...";
                    errorDiv.style.display = 'block';
                    setTimeout(() => { switchMode(true); passwordInput.value = email; passwordInput.focus(); }, 2500);
                } else if(msg.includes('User already registered')) {
                    errorDiv.textContent = "Ce compte existe déjà. Redirection vers la connexion...";
                    errorDiv.style.display = 'block';
                    setTimeout(() => { switchMode(false); passwordInput.focus(); }, 2000);
                } else if(msg.includes('Password should be')) {
                    errorDiv.textContent = "Le mot de passe doit faire au moins 6 caractères.";
                    errorDiv.style.display = 'block';
                } else {
                    errorDiv.textContent = "Erreur : " + msg;
                    errorDiv.style.display = 'block';
                }
            } finally {
                submitBtn.classList.remove('loading');
                if(submitBtn.textContent === 'Vérification...') {
                    submitBtn.textContent = origText;
                }
            }
        });
    }

    const navAuthBtn = document.getElementById('nav-auth-btn');
    if (navAuthBtn && supabaseClient) {
        supabaseClient.auth.getSession().then(({ data: { session }, error }) => {
            if (session) {
                // Connecté : Mise à jour du bouton avec icône user + Prénom
                const userName = session.user.user_metadata?.first_name || 'Mon Compte';
                navAuthBtn.innerHTML = `
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 8px; vertical-align: text-bottom;">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                        <circle cx="12" cy="7" r="4"></circle>
                    </svg>
                    ${userName}
                `;
                
                // Style dynamique du bouton navbar pour le rendre élégant
                navAuthBtn.classList.remove('btn-primary');
                navAuthBtn.style.color = 'var(--text-primary)';
                navAuthBtn.style.background = 'transparent';
                navAuthBtn.style.padding = '0';
                navAuthBtn.style.textTransform = 'uppercase';
                navAuthBtn.style.letterSpacing = '1px';
                navAuthBtn.style.fontSize = '0.9rem';
                navAuthBtn.style.display = 'inline-flex';
                navAuthBtn.style.alignItems = 'center';
                
                navAuthBtn.href = 'compte.html';

                // ==== LOGIQUE SPÉCIFIQUE DE LA PAGE COMPTE.HTML ====
                if (window.location.pathname.includes('compte.html')) {
                    // Pré-remplir les champs avec les données de Supabase
                    const emailInput = document.getElementById('profile-email');
                    const fnInput = document.getElementById('profile-firstname');
                    const lnInput = document.getElementById('profile-lastname');
                    const phoneInput = document.getElementById('profile-phone');
                    
                    if (emailInput) emailInput.value = session.user.email;
                    if (fnInput) fnInput.value = session.user.user_metadata?.first_name || '';
                    if (lnInput) lnInput.value = session.user.user_metadata?.last_name || '';
                    if (phoneInput) phoneInput.value = session.user.user_metadata?.phone || '';

                    // Action de déconnexion depuis la page compte
                    const logoutBtn = document.getElementById('logout-btn');
                    if(logoutBtn) {
                        logoutBtn.addEventListener('click', async (e) => {
                            e.preventDefault();
                            await supabaseClient.auth.signOut();
                            window.location.href = 'index.html';
                        });
                    }

                    // Enregistrement des modifications du profil
                    const profileForm = document.getElementById('profile-form');
                    const profileMsg = document.getElementById('profile-msg');
                    const profileSubmit = document.getElementById('profile-submit');

                    if(profileForm) {
                        profileForm.addEventListener('submit', async (e) => {
                            e.preventDefault();
                            profileSubmit.textContent = 'Enregistrement en cours...';
                            profileSubmit.style.opacity = '0.7';

                            const { data, error } = await supabaseClient.auth.updateUser({
                                data: { 
                                    first_name: fnInput.value.trim(),
                                    last_name: lnInput.value.trim(),
                                    phone: phoneInput.value.trim()
                                }
                            });

                            if(error) {
                                profileMsg.textContent = "Une erreur est survenue lors de la sauvegarde.";
                                profileMsg.style.color = '#d9534f';
                                profileMsg.style.background = '#fde8e8';
                            } else {
                                profileMsg.textContent = "Vos informations ont été mises à jour avec succès.";
                                profileMsg.style.color = '#2e7d32';
                                profileMsg.style.background = '#e8f5e9';
                                
                                // Rafraîchir instantanément le nom dans le menu
                                navAuthBtn.innerHTML = `
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 8px; vertical-align: text-bottom;">
                                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                                        <circle cx="12" cy="7" r="4"></circle>
                                    </svg>
                                    ${fnInput.value.trim() || 'Mon Compte'}
                                `;
                            }
                            profileMsg.style.display = 'block';
                            profileSubmit.textContent = 'Enregistrer les modifications';
                            profileSubmit.style.opacity = '1';
                            
                            setTimeout(() => { profileMsg.style.display = 'none'; }, 5000);
                        });
                    }
                }
            } else {
                // REDIRECTION DE SÉCURITÉ : Si on est sur compte.html et PAS connecté
                if (window.location.pathname.includes('compte.html')) {
                    window.location.href = 'login.html';
                }
            }
        }).catch(err => console.error(err));
    }
}

// Lancement immédiat garanti (ignore les bugs de cache ou de chargement différé)
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAuthLogic);
} else {
    initAuthLogic();
}
