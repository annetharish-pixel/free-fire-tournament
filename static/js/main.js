/**
 * FREE FIRE SQUAD TOURNAMENT PORTAL - FRONTEND SCRIPT
 */

document.addEventListener('DOMContentLoaded', () => {
    // --- APP STATE ---
    let currentStep = 1;
    let tournamentData = null;
    let activeProofTeamId = null;

    // --- DOM ELEMENTS ---
    const mobileNavToggle = document.getElementById('mobileNavToggle');
    const navLinks = document.getElementById('navLinks');
    
    // Forms & Inputs
    const registrationForm = document.getElementById('registrationForm');
    const screenshotDropzone = document.getElementById('screenshotDropzone');
    const screenshotInput = document.getElementById('payment_screenshot');
    const screenshotPreview = document.getElementById('screenshotPreview');
    const upiQrCodeImg = document.getElementById('upiQrCodeImg');
    const displayUpiId = document.getElementById('displayUpiId');
    const copyUpiBtn = document.getElementById('copyUpiBtn');

    // Modals
    const successModal = document.getElementById('successModal');
    const adminLoginModal = document.getElementById('adminLoginModal');
    const adminDashboardModal = document.getElementById('adminDashboardModal');
    const paymentProofModal = document.getElementById('paymentProofModal');

    // --- INITIALIZATION ---
    fetchTournamentInfo();
    fetchLeaderboard();
    checkAdminSession();
    setupEventListeners();

    // --- EVENT LISTENERS ---
    function setupEventListeners() {
        // Mobile Navigation Toggle
        mobileNavToggle?.addEventListener('click', () => {
            navLinks.classList.toggle('show');
        });

        // Close Mobile Nav when clicking links
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => navLinks.classList.remove('show'));
        });

        // Wizard Next/Prev Buttons
        document.getElementById('btnNext1')?.addEventListener('click', () => validateStep1() && goToStep(2));
        document.getElementById('btnPrev2')?.addEventListener('click', () => goToStep(1));
        document.getElementById('btnNext2')?.addEventListener('click', () => validateStep2() && goToStep(3));
        document.getElementById('btnPrev3')?.addEventListener('click', () => goToStep(2));

        // Screenshot Dropzone & Upload Preview
        screenshotDropzone?.addEventListener('click', () => screenshotInput.click());
        screenshotInput?.addEventListener('change', handleFilePreview);

        ['dragenter', 'dragover'].forEach(eventName => {
            screenshotDropzone?.addEventListener(eventName, (e) => {
                e.preventDefault();
                screenshotDropzone.style.borderColor = 'var(--neon-cyan)';
                screenshotDropzone.style.background = 'rgba(0, 243, 255, 0.15)';
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            screenshotDropzone?.addEventListener(eventName, (e) => {
                e.preventDefault();
                screenshotDropzone.style.borderColor = 'var(--border-cyan)';
                screenshotDropzone.style.background = 'rgba(0, 243, 255, 0.02)';
            });
        });

        screenshotDropzone?.addEventListener('drop', (e) => {
            if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                screenshotInput.files = e.dataTransfer.files;
                handleFilePreview();
            }
        });

        // Registration Form Submit
        registrationForm?.addEventListener('submit', handleRegistrationSubmit);

        // Copy UPI ID
        copyUpiBtn?.addEventListener('click', () => {
            copyToClipboard(displayUpiId.textContent.trim(), 'UPI ID copied to clipboard!');
        });

        // Success Modal Controls
        document.getElementById('closeSuccessModal')?.addEventListener('click', () => closeModal(successModal));
        document.getElementById('btnDoneSuccess')?.addEventListener('click', () => {
            closeModal(successModal);
            const teamId = document.getElementById('successTeamId').textContent.trim();
            document.getElementById('trackInput').value = teamId;
            document.getElementById('btnTrackStatus').click();
            document.getElementById('track').scrollIntoView({ behavior: 'smooth' });
        });
        document.getElementById('copyTeamIdBtn')?.addEventListener('click', () => {
            const teamId = document.getElementById('successTeamId').textContent.trim();
            copyToClipboard(teamId, 'Team ID copied to clipboard!');
        });

        // Track Registration Button
        document.getElementById('btnTrackStatus')?.addEventListener('click', handleTrackTeam);
        document.getElementById('trackInput')?.addEventListener('keyup', (e) => {
            if (e.key === 'Enter') handleTrackTeam();
        });

        // Admin Buttons & Modals
        document.getElementById('openAdminBtn')?.addEventListener('click', async () => {
            const isAuth = await checkAdminSession();
            if (isAuth) {
                openAdminDashboard();
            } else {
                openModal(adminLoginModal);
            }
        });

        document.getElementById('closeAdminLoginModal')?.addEventListener('click', () => closeModal(adminLoginModal));
        document.getElementById('closeAdminDashboardModal')?.addEventListener('click', () => closeModal(adminDashboardModal));
        document.getElementById('closePaymentProofModal')?.addEventListener('click', () => closeModal(paymentProofModal));

        // Admin Login Form
        document.getElementById('adminLoginForm')?.addEventListener('submit', handleAdminLogin);
        document.getElementById('adminLogoutBtn')?.addEventListener('click', handleAdminLogout);

        // Admin Dashboard Tabs
        document.querySelectorAll('.admin-tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.admin-tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.admin-tab-content').forEach(c => c.style.display = 'none');

                btn.classList.add('active');
                const targetTab = btn.dataset.tab;
                document.getElementById(targetTab).style.display = 'block';
            });
        });

        // Admin Search Team Input
        document.getElementById('admSearchTeam')?.addEventListener('input', filterAdminTeams);

        // Admin Forms
        document.getElementById('admSettingsForm')?.addEventListener('submit', handleAdminSettingsSave);
        document.getElementById('admLeaderboardForm')?.addEventListener('submit', handleAdminLeaderboardSave);

        // Proof Modal Approve/Reject Buttons
        document.getElementById('proofApproveBtn')?.addEventListener('click', () => updateTeamStatus(activeProofTeamId, 'Confirmed'));
        document.getElementById('proofRejectBtn')?.addEventListener('click', () => updateTeamStatus(activeProofTeamId, 'Rejected'));
    }

    // --- API FETCH FUNCTIONS ---

    async function fetchTournamentInfo() {
        try {
            const res = await fetch('/api/tournament-info');
            const result = await res.json();
            if (result.success) {
                tournamentData = result.data;
                renderTournamentInfo(tournamentData);
            }
        } catch (err) {
            console.error('Error loading tournament info:', err);
        }
    }

    function renderTournamentInfo(info) {
        // Hero values
        document.getElementById('heroEntryFee').textContent = `₹${info.fee} / Team`;
        document.getElementById('heroTeamSize').textContent = `${info.team_size} Players`;
        document.getElementById('heroPrizePool').textContent = info.prize_pool;
        document.getElementById('heroRegisteredTeams').textContent = `${info.registered_teams} / ${info.max_teams}`;

        const statusBadge = document.getElementById('regStatusBadge');
        if (info.status === 'Open') {
            statusBadge.textContent = 'REGISTRATION OPEN';
            statusBadge.parentElement.className = 'hero-tag badge-open';
        } else {
            statusBadge.textContent = 'REGISTRATION CLOSED';
            statusBadge.parentElement.className = 'hero-tag badge-closed';
        }

        // Specifications
        document.getElementById('infoGame').textContent = info.game;
        const regDateEl = document.getElementById('infoRegDate');
        if (regDateEl) regDateEl.textContent = info.reg_date || '12/09/2026';
        document.getElementById('infoDate').textContent = info.date || '13/09/2026';
        document.getElementById('infoMaxTeams').textContent = `${info.max_teams} Squads`;

        // Payment UPI QR & ID
        displayUpiId.textContent = info.upi_id;
        if (info.qr_code_url && info.qr_code_url.trim() !== '') {
            upiQrCodeImg.src = info.qr_code_url;
        } else if (!upiQrCodeImg.src || !upiQrCodeImg.src.includes('payment_qr_scanner')) {
            const upiPayUrl = `upi://pay?pa=${encodeURIComponent(info.upi_id)}&pn=${encodeURIComponent(info.name)}&am=${info.fee}&cu=INR`;
            upiQrCodeImg.src = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(upiPayUrl)}`;
        }

        // Contact info
        const waTextEl = document.getElementById('contactWhatsappText');
        const waBtnEl = document.getElementById('contactWhatsappBtn');
        const waContainer = document.getElementById('contactWhatsappContainer');

        if (waContainer && info.contact_whatsapp) {
            const rawNumbers = info.contact_whatsapp.split(/[,;\n/]+/).map(n => n.trim()).filter(Boolean);
            if (rawNumbers.length > 0) {
                waContainer.innerHTML = rawNumbers.map((num, idx) => {
                    const cleanDigits = num.replace(/\D/g, '');
                    const waUrl = cleanDigits.length === 10 ? `https://wa.me/91${cleanDigits}` : `https://wa.me/${cleanDigits}`;
                    const label = rawNumbers.length > 1 ? `WhatsApp Support ${idx + 1}` : `WhatsApp Support`;
                    return `
                        <div class="card-glass text-center" style="text-align: center;">
                            <i class="fa-brands fa-whatsapp text-green" style="font-size: 3rem; margin-bottom: 1rem;"></i>
                            <h3>${label}</h3>
                            <p style="font-size: 1.3rem; font-weight: 700; color: var(--neon-cyan); margin-bottom: 1.2rem;">${escapeHtml(num)}</p>
                            <a href="${waUrl}" target="_blank" class="btn btn-success" style="width: 100%;">
                                <i class="fa-brands fa-whatsapp"></i> Chat on WhatsApp
                            </a>
                        </div>
                    `;
                }).join('');
            }
        } else {
            if (waTextEl) waTextEl.textContent = info.contact_whatsapp;
            if (waBtnEl) waBtnEl.href = `https://wa.me/${info.contact_whatsapp.replace(/\D/g, '')}`;
        }

        // Rules List
        renderRules(info.rules);
    }

    function renderRules(rulesText) {
        const container = document.getElementById('rulesListContainer');
        container.innerHTML = '';

        const rulesArray = rulesText.split('\n').filter(r => r.trim().length > 0);
        rulesArray.forEach((rule, idx) => {
            const cleanRule = rule.replace(/^\d+[\.\)]\s*/, '');
            const card = document.createElement('div');
            card.className = 'rule-card';
            card.innerHTML = `
                <div class="rule-number">${idx + 1}</div>
                <div class="rule-content">
                    <h4>Rule #${idx + 1}</h4>
                    <p>${cleanRule}</p>
                </div>
            `;
            container.appendChild(card);
        });
    }

    async function fetchLeaderboard() {
        try {
            const res = await fetch('/api/leaderboard');
            const result = await res.json();
            if (result.success) {
                renderLeaderboard(result.data);
            }
        } catch (err) {
            console.error('Error fetching leaderboard:', err);
        }
    }

    function renderLeaderboard(data) {
        const tbody = document.getElementById('leaderboardTbody');
        tbody.innerHTML = '';

        if (!data || data.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;" class="text-muted">No leaderboard rankings recorded yet.</td></tr>`;
            return;
        }

        data.forEach(item => {
            const tr = document.createElement('tr');
            let rankPillClass = '';
            if (item.rank === 1) rankPillClass = 'rank-1';
            else if (item.rank === 2) rankPillClass = 'rank-2';
            else if (item.rank === 3) rankPillClass = 'rank-3';

            const rankBadge = item.rank <= 3 
                ? `<span class="rank-pill ${rankPillClass}">${item.rank}</span>`
                : `<span>#${item.rank}</span>`;

            tr.innerHTML = `
                <td>${rankBadge}</td>
                <td><strong>${escapeHtml(item.team_name)}</strong></td>
                <td><strong class="text-cyan">${item.points} pts</strong></td>
                <td>${item.kills} kills</td>
                <td><span class="text-gold">${item.booyahs} 🏆</span></td>
            `;
            tbody.appendChild(tr);
        });
    }

    // --- FORM WIZARD LOGIC & VALIDATION ---

    function goToStep(stepNumber) {
        currentStep = stepNumber;

        document.querySelectorAll('.form-step').forEach((el, idx) => {
            el.classList.toggle('active', (idx + 1) === stepNumber);
        });

        for (let i = 1; i <= 4; i++) {
            const indicator = document.getElementById(`stepIndicator${i}`);
            indicator.classList.remove('active', 'completed');
            if (i === stepNumber) {
                indicator.classList.add('active');
            } else if (i < stepNumber) {
                indicator.classList.add('completed');
            }
        }
    }

    function validateStep1() {
        const teamName = document.getElementById('team_name').value.trim();
        const leaderName = document.getElementById('leader_name').value.trim();
        const mobile = document.getElementById('mobile').value.trim();
        const email = document.getElementById('email').value.trim();

        if (!teamName) {
            showToast('Please enter your Team Name.', 'error');
            return false;
        }
        if (!leaderName) {
            showToast('Please enter the Team Leader Full Name.', 'error');
            return false;
        }

        const cleanMobile = mobile.replace(/\D/g, '');
        if (cleanMobile.length < 10) {
            showToast('Please enter a valid 10-digit mobile number.', 'error');
            return false;
        }

        const emailRegex = /^[\w\.-]+@[\w\.-]+\.\w+$/;
        if (!emailRegex.test(email)) {
            showToast('Please enter a valid email address.', 'error');
            return false;
        }

        return true;
    }

    function validateStep2() {
        const uids = [];
        for (let i = 1; i <= 4; i++) {
            const pName = document.getElementById(`p${i}_name`).value.trim();
            const pUid = document.getElementById(`p${i}_uid`).value.trim();

            if (!pName || !pUid) {
                showToast(`Please fill out all details for Player ${i}. All 4 players are mandatory.`, 'error');
                return false;
            }

            uids.push(pUid);
        }

        // Check internal duplicate UIDs
        if (new Set(uids).size < 4) {
            showToast('Duplicate Free Fire UIDs detected among your squad members.', 'error');
            return false;
        }

        return true;
    }

    function handleFilePreview() {
        const file = screenshotInput.files[0];
        if (file) {
            if (file.size > 5 * 1024 * 1024) {
                showToast('Screenshot file size exceeds 5MB limit.', 'error');
                screenshotInput.value = '';
                screenshotPreview.style.display = 'none';
                return;
            }

            const reader = new FileReader();
            reader.onload = (e) => {
                screenshotPreview.src = e.target.result;
                screenshotPreview.style.display = 'block';
            };
            reader.readAsDataURL(file);
        }
    }

    async function handleRegistrationSubmit(e) {
        e.preventDefault();

        if (!validateStep1() || !validateStep2()) return;

        const transactionId = document.getElementById('transaction_id').value.trim();
        if (!transactionId) {
            showToast('Please enter the UPI Transaction ID / Ref No.', 'error');
            return;
        }

        if (!screenshotInput.files[0]) {
            showToast('Please upload payment proof screenshot.', 'error');
            return;
        }

        const submitBtn = document.getElementById('btnSubmitForm');
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> SUBMITTING REGISTRATION...`;

        try {
            const formData = new FormData(registrationForm);
            const res = await fetch('/api/register', {
                method: 'POST',
                body: formData
            });

            const result = await res.json();
            if (result.success) {
                showToast(result.message || 'Registration successful! Confirmation email has been sent to your registered email.', result.email_sent === false ? 'info' : 'success');
                
                // Set Modal Data
                if (document.getElementById('successTeamId')) {
                    document.getElementById('successTeamId').textContent = result.data.team_id;
                }
                if (document.getElementById('successTeamName')) {
                    document.getElementById('successTeamName').textContent = result.data.team_name;
                }
                
                // Reset Form
                registrationForm.reset();
                screenshotPreview.style.display = 'none';
                goToStep(1);

                // Open Success Modal
                openModal(successModal);

                // Refresh Hero numbers
                fetchTournamentInfo();

            } else {
                showToast(result.message || 'Registration failed.', 'error');
            }
        } catch (err) {
            console.error('Registration submit error:', err);
            showToast('Server error while submitting registration.', 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    }

    // --- TRACK REGISTRATION FUNCTION ---

    async function handleTrackTeam() {
        const query = document.getElementById('trackInput').value.trim();
        const container = document.getElementById('statusResultContainer');

        if (!query) {
            showToast('Please enter a Team ID or Team Name to search.', 'error');
            return;
        }

        container.style.display = 'block';
        container.innerHTML = `<div style="text-align:center; padding: 2rem;"><i class="fa-solid fa-spinner fa-spin text-cyan" style="font-size: 2rem;"></i><p style="margin-top:0.8rem;">Fetching team status...</p></div>`;

        try {
            const res = await fetch(`/api/track/${encodeURIComponent(query)}`);
            const result = await res.json();

            if (!result.success) {
                container.innerHTML = `
                    <div style="text-align: center; padding: 2rem;">
                        <i class="fa-solid fa-triangle-exclamation text-red" style="font-size: 3rem; margin-bottom: 1rem;"></i>
                        <h3 class="text-red">TEAM NOT FOUND</h3>
                        <p class="text-muted">${escapeHtml(result.message)}</p>
                    </div>
                `;
                return;
            }

            const { team, players, payment } = result.data;
            let statusBadge = '';
            let statusMessage = '';

            if (team.registration_status === 'Confirmed') {
                statusBadge = `<span class="status-badge-lg badge-confirmed"><i class="fa-solid fa-circle-check"></i> CONFIRMED</span>`;
                statusMessage = `Your team registration and ₹200 payment have been verified! Match room details will be sent to Leader's WhatsApp.`;
            } else if (team.registration_status === 'Rejected') {
                statusBadge = `<span class="status-badge-lg badge-closed"><i class="fa-solid fa-circle-xmark"></i> REJECTED</span>`;
                statusMessage = `Your registration or payment verification was rejected. Please contact the tournament organizer immediately.`;
            } else {
                statusBadge = `<span class="status-badge-lg badge-pending"><i class="fa-solid fa-clock"></i> PENDING VERIFICATION</span>`;
                statusMessage = `Your payment proof (UTR: ${escapeHtml(payment.transaction_id || 'N/A')}) is waiting for organizer verification.`;
            }

            let playersHtml = players.map(p => `
                <div class="stat-box" style="text-align: left;">
                    <div class="stat-label">Player ${p.player_number}</div>
                    <div style="font-weight: 700; color: var(--text-primary); margin-top: 0.2rem;">${escapeHtml(p.player_name)}</div>
                    <div style="font-size: 0.85rem; color: var(--neon-cyan);">UID: ${escapeHtml(p.free_fire_uid)}</div>
                </div>
            `).join('');

            container.innerHTML = `
                <div style="text-align: center; margin-bottom: 2rem;">
                    <div class="stat-label">TEAM REGISTRATION CARD</div>
                    <h2 class="text-cyan glow-cyan" style="margin-top: 0.4rem;">${escapeHtml(team.team_name)}</h2>
                    <div style="font-family: var(--font-heading); font-size: 1.2rem; color: var(--gold-accent); margin-top: 0.2rem;">TEAM ID: ${escapeHtml(team.team_id)}</div>
                    ${statusBadge}
                    <p class="text-muted" style="max-width: 600px; margin: 0 auto;">${statusMessage}</p>
                </div>

                <div class="form-grid" style="margin-bottom: 2rem;">
                    <div class="stat-box">
                        <div class="stat-label">Team Leader</div>
                        <div class="stat-value" style="font-size: 1.1rem;">${escapeHtml(team.leader_name)}</div>
                        <div style="font-size: 0.85rem;" class="text-muted">📱 ${escapeHtml(team.mobile)}</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Entry Fee Payment</div>
                        <div class="stat-value text-green" style="font-size: 1.1rem;">₹200 (${escapeHtml(payment.payment_status || 'Pending')})</div>
                        <div style="font-size: 0.85rem;" class="text-muted">UTR: ${escapeHtml(payment.transaction_id || 'N/A')}</div>
                    </div>
                </div>

                <h4 class="text-cyan" style="margin-bottom: 1rem;"><i class="fa-solid fa-users"></i> Registered Squad Roster (4 Players)</h4>
                <div class="form-grid">
                    ${playersHtml}
                </div>
            `;

        } catch (err) {
            console.error('Error tracking team:', err);
            showToast('Error tracking registration.', 'error');
        }
    }

    // --- ADMIN PORTAL LOGIC ---

    async function checkAdminSession() {
        try {
            const res = await fetch('/api/admin/check-auth');
            const data = await res.json();
            return data.authenticated;
        } catch (err) {
            return false;
        }
    }

    async function handleAdminLogin(e) {
        e.preventDefault();
        const username = document.getElementById('adminUsername').value.trim();
        const password = document.getElementById('adminPassword').value.trim();

        try {
            const res = await fetch('/api/admin/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            const result = await res.json();
            if (result.success) {
                showToast('Admin login successful!', 'success');
                closeModal(adminLoginModal);
                openAdminDashboard();
            } else {
                showToast(result.message || 'Invalid admin credentials.', 'error');
            }
        } catch (err) {
            showToast('Login server error.', 'error');
        }
    }

    async function handleAdminLogout() {
        await fetch('/api/admin/logout', { method: 'POST' });
        showToast('Logged out of admin panel.', 'success');
        closeModal(adminDashboardModal);
    }

    async function openAdminDashboard() {
        openModal(adminDashboardModal);
        loadAdminDashboardData();
        loadAdminTeams();
        loadAdminSettings();
        loadAdminLeaderboard();
    }

    async function loadAdminDashboardData() {
        try {
            const res = await fetch('/api/admin/dashboard');
            const result = await res.json();
            if (result.success) {
                const d = result.data;
                document.getElementById('admTotalTeams').textContent = d.total_teams;
                document.getElementById('admConfirmedTeams').textContent = d.confirmed_teams;
                document.getElementById('admPendingTeams').textContent = d.pending_teams;
                document.getElementById('admTotalPlayers').textContent = d.total_players;
                document.getElementById('admTotalCollected').textContent = `₹${d.total_collected}`;
                document.getElementById('admTabTeamCount').textContent = d.total_teams;
            }
        } catch (err) {
            console.error('Error loading admin dashboard stats:', err);
        }
    }

    let allAdminTeamsData = [];

    async function loadAdminTeams() {
        try {
            const res = await fetch('/api/admin/teams');
            const result = await res.json();
            if (result.success) {
                allAdminTeamsData = result.data;
                renderAdminTeamsTable(allAdminTeamsData);
            }
        } catch (err) {
            console.error('Error loading admin teams:', err);
        }
    }

    function renderAdminTeamsTable(teams) {
        const tbody = document.getElementById('admTeamsTbody');
        tbody.innerHTML = '';

        if (!teams || teams.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;" class="text-muted">No team registrations found.</td></tr>`;
            return;
        }

        teams.forEach(team => {
            const tr = document.createElement('tr');
            const statusBadge = team.registration_status === 'Confirmed' 
                ? `<span class="badge badge-confirmed">Confirmed</span>`
                : (team.registration_status === 'Rejected' 
                    ? `<span class="badge badge-closed">Rejected</span>`
                    : `<span class="badge badge-pending">Pending</span>`);

            const screenshotBtn = team.payment && team.payment.payment_screenshot 
                ? `<button class="btn btn-secondary btn-sm view-proof-btn" data-teamid="${team.team_id}" data-utr="${team.payment.transaction_id}" data-img="${team.payment.payment_screenshot}">
                    <i class="fa-solid fa-image"></i> View Proof
                   </button>`
                : `<span class="text-muted">No proof</span>`;

            tr.innerHTML = `
                <td><strong class="text-cyan">${team.team_id}</strong></td>
                <td><strong>${escapeHtml(team.team_name)}</strong></td>
                <td>${escapeHtml(team.leader_name)}<br><small class="text-muted">📱 ${escapeHtml(team.mobile)}</small></td>
                <td><button class="btn btn-secondary btn-sm view-players-btn" data-teamid="${team.team_id}"><i class="fa-solid fa-users"></i> 4 Players</button></td>
                <td><code>${escapeHtml(team.payment.transaction_id || 'N/A')}</code></td>
                <td>${screenshotBtn}</td>
                <td>${statusBadge}</td>
                <td>
                    <div style="display:flex; gap:0.4rem;">
                        <button class="btn btn-success btn-sm approve-team-btn" data-teamid="${team.team_id}"><i class="fa-solid fa-check"></i></button>
                        <button class="btn btn-danger btn-sm reject-team-btn" data-teamid="${team.team_id}"><i class="fa-solid fa-xmark"></i></button>
                        <button class="btn btn-danger btn-sm delete-team-btn" data-teamid="${team.team_id}"><i class="fa-solid fa-trash"></i></button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });

        // Event delegation for table action buttons
        tbody.querySelectorAll('.view-proof-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                activeProofTeamId = btn.dataset.teamid;
                document.getElementById('proofTeamTitle').textContent = `Team ${btn.dataset.teamid} - UTR: ${btn.dataset.utr}`;
                document.getElementById('proofModalImg').src = `/uploads/payments/${btn.dataset.img}`;
                openModal(paymentProofModal);
            });
        });

        tbody.querySelectorAll('.view-players-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const team = allAdminTeamsData.find(t => t.team_id === btn.dataset.teamid);
                if (team) {
                    const pList = team.players.map(p => `Player ${p.player_number}: ${p.player_name} (UID: ${p.free_fire_uid})`).join('\n');
                    alert(`Squad Roster for ${team.team_name} (${team.team_id}):\n\n${pList}`);
                }
            });
        });

        tbody.querySelectorAll('.approve-team-btn').forEach(btn => {
            btn.addEventListener('click', () => updateTeamStatus(btn.dataset.teamid, 'Confirmed'));
        });

        tbody.querySelectorAll('.reject-team-btn').forEach(btn => {
            btn.addEventListener('click', () => updateTeamStatus(btn.dataset.teamid, 'Rejected'));
        });

        tbody.querySelectorAll('.delete-team-btn').forEach(btn => {
            btn.addEventListener('click', () => deleteTeam(btn.dataset.teamid));
        });
    }

    function filterAdminTeams() {
        const query = document.getElementById('admSearchTeam').value.toLowerCase().trim();
        const filtered = allAdminTeamsData.filter(t => 
            t.team_id.toLowerCase().includes(query) ||
            t.team_name.toLowerCase().includes(query) ||
            t.leader_name.toLowerCase().includes(query) ||
            t.mobile.includes(query)
        );
        renderAdminTeamsTable(filtered);
    }

    async function updateTeamStatus(teamId, status) {
        try {
            const res = await fetch(`/api/admin/team/${teamId}/status`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status })
            });
            const result = await res.json();
            if (result.success) {
                showToast(`Team ${teamId} status updated to ${status}.`, 'success');
                closeModal(paymentProofModal);
                loadAdminDashboardData();
                loadAdminTeams();
                fetchTournamentInfo();
            } else {
                showToast(result.message, 'error');
            }
        } catch (err) {
            showToast('Error updating team status.', 'error');
        }
    }

    async function deleteTeam(teamId) {
        if (!confirm(`Are you sure you want to permanently delete Team ${teamId}?`)) return;

        try {
            const res = await fetch(`/api/admin/team/${teamId}`, { method: 'DELETE' });
            const result = await res.json();
            if (result.success) {
                showToast(`Team ${teamId} deleted successfully.`, 'success');
                loadAdminDashboardData();
                loadAdminTeams();
                fetchTournamentInfo();
            } else {
                showToast(result.message, 'error');
            }
        } catch (err) {
            showToast('Error deleting team.', 'error');
        }
    }

    async function loadAdminSettings() {
        if (!tournamentData) await fetchTournamentInfo();
        if (tournamentData) {
            document.getElementById('admSetTitle').value = tournamentData.name;
            document.getElementById('admSetRegStatus').value = tournamentData.status;
            document.getElementById('admSetMaxTeams').value = tournamentData.max_teams;
            document.getElementById('admSetFee').value = tournamentData.fee;
            document.getElementById('admSetPrizePool').value = tournamentData.prize_pool;
            document.getElementById('admSetUpiId').value = tournamentData.upi_id;
            document.getElementById('admSetDate').value = tournamentData.date;
            document.getElementById('admSetRules').value = tournamentData.rules;
            if (document.getElementById('admSetRegDate')) {
                document.getElementById('admSetRegDate').value = tournamentData.reg_date || '';
            }
            if (document.getElementById('admSetWhatsapp')) {
                document.getElementById('admSetWhatsapp').value = tournamentData.contact_whatsapp || '';
            }
            const admQrPreview = document.getElementById('admQrPreview');
            if (admQrPreview) {
                if (tournamentData.qr_code_url && tournamentData.qr_code_url.trim() !== '') {
                    admQrPreview.src = tournamentData.qr_code_url;
                } else {
                    admQrPreview.src = '/static/images/payment_qr_scanner.jpg';
                }
            }
        }
    }

    async function handleAdminSettingsSave(e) {
        e.preventDefault();
        const payload = {
            name: document.getElementById('admSetTitle').value.trim(),
            status: document.getElementById('admSetRegStatus').value,
            max_teams: parseInt(document.getElementById('admSetMaxTeams').value) || 12,
            fee: parseFloat(document.getElementById('admSetFee').value),
            prize_pool: document.getElementById('admSetPrizePool').value.trim(),
            upi_id: document.getElementById('admSetUpiId').value.trim(),
            reg_date: document.getElementById('admSetRegDate') ? document.getElementById('admSetRegDate').value.trim() : (tournamentData ? tournamentData.reg_date : '12/09/2026'),
            date: document.getElementById('admSetDate').value.trim(),
            time: tournamentData ? tournamentData.time : 'To be announced',
            game: tournamentData ? tournamentData.game : 'Free Fire',
            team_size: 4,
            rules: document.getElementById('admSetRules').value.trim(),
            contact_whatsapp: document.getElementById('admSetWhatsapp') ? document.getElementById('admSetWhatsapp').value.trim() : (tournamentData ? tournamentData.contact_whatsapp : '+91 90525 96711, +91 93981 33478'),
            contact_instagram: tournamentData ? tournamentData.contact_instagram : '@ff_squad_battle',
            contact_email: tournamentData ? tournamentData.contact_email : 'support@ffsquadbattle.com'
        };

        try {
            const res = await fetch('/api/admin/tournament-info', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await res.json();
            if (result.success) {
                showToast('Tournament settings saved successfully!', 'success');
                fetchTournamentInfo();
            } else {
                showToast(result.message, 'error');
            }
        } catch (err) {
            showToast('Error saving settings.', 'error');
        }
    }

    async function loadAdminLeaderboard() {
        try {
            const res = await fetch('/api/leaderboard');
            const result = await res.json();
            if (result.success) {
                const tbody = document.getElementById('admLbTbody');
                tbody.innerHTML = '';
                result.data.forEach(item => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>#${item.rank}</td>
                        <td><strong>${escapeHtml(item.team_name)}</strong></td>
                        <td>${item.points}</td>
                        <td>${item.kills}</td>
                        <td>${item.booyahs}</td>
                        <td>
                            <button class="btn btn-danger btn-sm delete-lb-btn" data-id="${item.id}"><i class="fa-solid fa-trash"></i></button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });

                tbody.querySelectorAll('.delete-lb-btn').forEach(btn => {
                    btn.addEventListener('click', async () => {
                        await fetch(`/api/admin/leaderboard/${btn.dataset.id}`, { method: 'DELETE' });
                        showToast('Leaderboard entry deleted.', 'success');
                        loadAdminLeaderboard();
                        fetchLeaderboard();
                    });
                });
            }
        } catch (err) {
            console.error('Error loading admin leaderboard:', err);
        }
    }

    async function handleAdminLeaderboardSave(e) {
        e.preventDefault();
        const payload = {
            id: document.getElementById('admLbId').value || null,
            rank: parseInt(document.getElementById('admLbRank').value),
            team_name: document.getElementById('admLbTeamName').value.trim(),
            points: parseInt(document.getElementById('admLbPoints').value || 0),
            kills: parseInt(document.getElementById('admLbKills').value || 0),
            booyahs: parseInt(document.getElementById('admLbBooyahs').value || 0)
        };

        try {
            const res = await fetch('/api/admin/leaderboard', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await res.json();
            if (result.success) {
                showToast('Leaderboard entry saved!', 'success');
                document.getElementById('admLeaderboardForm').reset();
                loadAdminLeaderboard();
                fetchLeaderboard();
            } else {
                showToast(result.message, 'error');
            }
        } catch (err) {
            showToast('Error saving leaderboard entry.', 'error');
        }
    }

    // --- HELPER UTILITIES ---

    function openModal(modalEl) {
        modalEl?.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function closeModal(modalEl) {
        modalEl?.classList.remove('active');
        document.body.style.overflow = 'auto';
    }

    function copyToClipboard(text, successMsg) {
        navigator.clipboard.writeText(text).then(() => {
            showToast(successMsg, 'success');
        }).catch(() => {
            showToast('Failed to copy to clipboard.', 'error');
        });
    }

    function showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        const icon = type === 'success' ? 'fa-circle-check text-green' : (type === 'error' ? 'fa-circle-exclamation text-red' : 'fa-circle-info text-cyan');
        
        toast.innerHTML = `
            <i class="fa-solid ${icon}"></i>
            <span>${escapeHtml(message)}</span>
        `;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideInRight 0.3s reverse ease';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
    const admQrUploadBtn = document.getElementById('admQrUploadBtn');
    if (admQrUploadBtn) {
        admQrUploadBtn.addEventListener('click', async () => {
            const fileInput = document.getElementById('admQrFileInput');
            if (!fileInput || !fileInput.files[0]) {
                showToast('Please select a QR scanner photo file first.', 'error');
                return;
            }
            const formData = new FormData();
            formData.append('qr_photo', fileInput.files[0]);

            admQrUploadBtn.disabled = true;
            admQrUploadBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Uploading...';

            try {
                const res = await fetch('/api/admin/upload-qr', {
                    method: 'POST',
                    body: formData
                });
                const result = await res.json();
                if (result.success) {
                    showToast('QR Scanner photo updated successfully!', 'success');
                    fileInput.value = '';
                    if (result.qr_code_url) {
                        const admQrPreview = document.getElementById('admQrPreview');
                        if (admQrPreview) admQrPreview.src = result.qr_code_url;
                    }
                    fetchTournamentInfo();
                } else {
                    showToast(result.message, 'error');
                }
            } catch (err) {
                showToast('Error uploading QR scanner photo.', 'error');
            } finally {
                admQrUploadBtn.disabled = false;
                admQrUploadBtn.innerHTML = '<i class="fa-solid fa-upload"></i> Upload New Scanner Photo';
            }
        });
    }

    const admQrResetBtn = document.getElementById('admQrResetBtn');
    if (admQrResetBtn) {
        admQrResetBtn.addEventListener('click', async () => {
            if (!confirm('Reset QR scanner photo to default?')) return;
            try {
                const res = await fetch('/api/admin/reset-qr', { method: 'POST' });
                const result = await res.json();
                if (result.success) {
                    showToast('QR scanner reset to default.', 'success');
                    const admQrPreview = document.getElementById('admQrPreview');
                    if (admQrPreview) admQrPreview.src = '/static/images/payment_qr_scanner.jpg';
                    fetchTournamentInfo();
                } else {
                    showToast(result.message, 'error');
                }
            } catch (err) {
                showToast('Error resetting QR scanner photo.', 'error');
            }
        });
    }
});
