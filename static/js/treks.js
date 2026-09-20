/**
 * AMU Treks - Dynamic Filter, Saved Treks Wishlist & Interaction Controller
 */

let allTreks = [];
let activeSeason = null;
let savedTreks = [];

document.addEventListener('DOMContentLoaded', () => {
    allTreks = typeof INITIAL_TREKS_DATA !== 'undefined' ? INITIAL_TREKS_DATA : [];
    initChatbot();
    initChecklist();
    initSavedTreks();
    initFilters();
});

/* ==========================================
   Saved Treks / Wishlist Management
   ========================================== */
function initSavedTreks() {
    const stored = localStorage.getItem('amu_saved_treks');
    if (stored !== null) {
        try {
            savedTreks = JSON.parse(stored);
        } catch (e) {
            savedTreks = ['kedarkantha', 'kashmir-great-lakes', 'everest-base-camp'];
        }
    } else {
        // Default favorites to showcase on initial load
        savedTreks = ['kedarkantha', 'kashmir-great-lakes', 'everest-base-camp'];
        localStorage.setItem('amu_saved_treks', JSON.stringify(savedTreks));
    }
    updateSavedUI();
}

function saveSavedTreksToStorage() {
    localStorage.setItem('amu_saved_treks', JSON.stringify(savedTreks));
    updateSavedUI();
}

function toggleSaveTrek(trekId) {
    const idx = savedTreks.indexOf(trekId);
    if (idx > -1) {
        savedTreks.splice(idx, 1);
    } else {
        savedTreks.push(trekId);
    }
    saveSavedTreksToStorage();
    
    // Update modal button if currently open for this trek
    const modalSaveBtn = document.getElementById('modalSaveBtn');
    if (modalSaveBtn) {
        const isSaved = savedTreks.includes(trekId);
        modalSaveBtn.className = isSaved ? 'btn-modal-save-heart saved' : 'btn-modal-save-heart';
        modalSaveBtn.innerHTML = `<i class="${isSaved ? 'fa-solid fa-heart' : 'fa-regular fa-heart'}"></i>`;
        modalSaveBtn.title = isSaved ? 'Remove from Saved Treks' : 'Save Trek to Wishlist';
    }
}

function removeSavedTrek(trekId, event) {
    if (event) {
        event.stopPropagation();
    }
    const idx = savedTreks.indexOf(trekId);
    if (idx > -1) {
        savedTreks.splice(idx, 1);
        saveSavedTreksToStorage();
    }
}

function clearAllSavedTreks() {
    savedTreks = [];
    saveSavedTreksToStorage();
}

function updateSavedUI() {
    // 1. Update Badge on Navbar Heart Button
    const badge = document.getElementById('savedTreksBadge');
    if (badge) {
        badge.textContent = savedTreks.length;
        badge.style.display = savedTreks.length > 0 ? 'inline-flex' : 'none';
    }

    // 1b. Update Badge on Mobile Bottom Navigation
    const mobileBadge = document.getElementById('mobileSavedBadge');
    if (mobileBadge) {
        mobileBadge.textContent = savedTreks.length;
        mobileBadge.style.display = savedTreks.length > 0 ? 'inline-flex' : 'none';
    }

    // 2. Update Count Pill in Popover Header
    const popoverCount = document.getElementById('savedPopoverCount');
    if (popoverCount) {
        popoverCount.textContent = savedTreks.length;
    }

    // 3. Update Popover List Content
    renderSavedTreksList();

    // 4. Update Borderless Heart Icons in Location Row on All Trek Cards
    allTreks.forEach(trek => {
        const heartBtn = document.getElementById(`cardSaveHeart-${trek.id}`);
        if (heartBtn) {
            const isSaved = savedTreks.includes(trek.id);
            if (isSaved) {
                heartBtn.className = 'btn-card-save-heart saved';
                heartBtn.innerHTML = '<i class="fa-solid fa-heart"></i>';
                heartBtn.title = 'Remove from Saved Treks';
            } else {
                heartBtn.className = 'btn-card-save-heart';
                heartBtn.innerHTML = '<i class="fa-regular fa-heart"></i>';
                heartBtn.title = 'Save Trek to Wishlist';
            }
        }
    });
}

function renderSavedTreksList() {
    const listEl = document.getElementById('savedTreksList');
    const footerEl = document.getElementById('savedPopoverFooter');
    if (!listEl) return;

    const savedItems = allTreks.filter(t => savedTreks.includes(t.id));

    if (savedItems.length === 0) {
        listEl.innerHTML = `
            <div class="saved-empty-state">
                <i class="fa-regular fa-heart empty-heart-icon"></i>
                <p class="saved-empty-title">No Saved Treks</p>
                <p class="saved-empty-sub">Explore the trails and click the heart icon on any trek to bookmark your favorites.</p>
            </div>
        `;
        if (footerEl) footerEl.style.display = 'none';
        return;
    }

    if (footerEl) footerEl.style.display = 'flex';

    listEl.innerHTML = savedItems.map(trek => `
        <div class="saved-popover-item" onclick="openTrekModal('${trek.id}')">
            <img src="${trek.image}" alt="${trek.name}" class="saved-popover-img" loading="lazy">
            <div class="saved-popover-info">
                <span class="saved-popover-region"><i class="fa-solid fa-location-dot"></i> ${trek.region}</span>
                <h4 class="saved-popover-name">${trek.name}</h4>
                <div class="saved-popover-meta">
                    <span>${trek.duration_days} Days • ${trek.max_altitude_text || trek.max_altitude_ft + ' ft'}</span>
                </div>
                <div class="saved-popover-bottom">
                    <strong class="saved-popover-price">${trek.price}</strong>
                    <span class="saved-popover-view">View <i class="fa-solid fa-arrow-right"></i></span>
                </div>
            </div>
            <button type="button" class="btn-remove-saved" onclick="removeSavedTrek('${trek.id}', event)" title="Remove from Saved">
                <i class="fa-solid fa-xmark"></i>
            </button>
        </div>
    `).join('');
}

function toggleSavedTreksPopover(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const popover = document.getElementById('savedTreksPopover');
    const btn = document.getElementById('savedTreksBtn');
    if (!popover) return;

    // Close chatbot popover if open
    const chatbotPopover = document.getElementById('chatbotPopover');
    const chatbotBtn = document.getElementById('trekChatbotBtn');
    if (chatbotPopover && chatbotPopover.classList.contains('show')) {
        chatbotPopover.classList.remove('show');
        if (chatbotBtn) chatbotBtn.classList.remove('active');
    }

    // Close checklist popover if open
    const checklistPopover = document.getElementById('checklistPopover');
    const checklistBtn = document.getElementById('trekChecklistBtn');
    if (checklistPopover && checklistPopover.classList.contains('show')) {
        checklistPopover.classList.remove('show');
        if (checklistBtn) checklistBtn.classList.remove('active');
    }

    // Close profile popover if open
    const profileMenu = document.getElementById('profilePopoverMenu');
    const profileBtn = document.getElementById('profileDropdownBtn');
    if (profileMenu && profileMenu.classList.contains('show')) {
        profileMenu.classList.remove('show');
        if (profileBtn) profileBtn.classList.remove('active');
    }

    const isShown = popover.classList.contains('show');
    if (isShown) {
        popover.classList.remove('show');
        if (btn) btn.classList.remove('active');
    } else {
        popover.classList.add('show');
        if (btn) btn.classList.add('active');
    }
}

/* ==========================================
   Filter & Search Controls
   ========================================== */
function initFilters() {
    const searchFilter = document.getElementById('searchFilter');
    const monthFilter = document.getElementById('monthFilter');
    const difficultyFilter = document.getElementById('difficultyFilter');
    const regionFilter = document.getElementById('regionFilter');
    const durationFilter = document.getElementById('durationFilter');
    const seasonFilter = document.getElementById('seasonFilter');

    if (searchFilter) searchFilter.addEventListener('input', applyFilters);
    if (monthFilter) monthFilter.addEventListener('change', applyFilters);
    if (difficultyFilter) difficultyFilter.addEventListener('change', applyFilters);
    if (regionFilter) regionFilter.addEventListener('change', applyFilters);
    if (durationFilter) durationFilter.addEventListener('change', applyFilters);
    if (seasonFilter) seasonFilter.addEventListener('change', applyFilters);
}

function applyFilters() {
    const searchQuery = (document.getElementById('searchFilter')?.value || '').trim().toLowerCase();
    const monthVal = document.getElementById('monthFilter')?.value || 'all';
    const diffVal = document.getElementById('difficultyFilter')?.value || 'all';
    const regionVal = document.getElementById('regionFilter')?.value || 'all';
    const durationVal = document.getElementById('durationFilter')?.value || 'all';
    const seasonVal = document.getElementById('seasonFilter')?.value || 'all';
    const sortBy = document.getElementById('sortSelector')?.value || 'featured';

    const cards = document.querySelectorAll('.trek-card');
    let visibleCount = 0;

    cards.forEach(card => {
        const id = card.getAttribute('data-id');
        const name = (card.getAttribute('data-name') || '').toLowerCase();
        const region = card.getAttribute('data-region') || '';
        const diff = card.getAttribute('data-difficulty') || '';
        const months = (card.getAttribute('data-months') || '').split(',');
        const season = card.getAttribute('data-season') || '';
        const days = parseInt(card.getAttribute('data-days') || '0', 10);

        let matchesSearch = true;
        if (searchQuery) {
            matchesSearch = name.includes(searchQuery) || region.toLowerCase().includes(searchQuery);
        }

        let matchesMonth = true;
        if (monthVal !== 'all') {
            matchesMonth = months.includes(monthVal);
        }

        let matchesSeason = true;
        if (seasonVal !== 'all') {
            matchesSeason = season.toLowerCase().includes(seasonVal.toLowerCase());
        }

        let matchesDiff = true;
        if (diffVal !== 'all') {
            matchesDiff = diff === diffVal;
        }

        let matchesRegion = true;
        if (regionVal !== 'all') {
            matchesRegion = region.toLowerCase().includes(regionVal.toLowerCase());
        }

        let matchesDuration = true;
        if (durationVal === 'short') {
            matchesDuration = days <= 5;
        } else if (durationVal === 'medium') {
            matchesDuration = days >= 6 && days <= 8;
        } else if (durationVal === 'long') {
            matchesDuration = days >= 9;
        }

        const isVisible = matchesSearch && matchesMonth && matchesSeason && matchesDiff && matchesRegion && matchesDuration;

        if (isVisible) {
            card.style.display = 'flex';
            visibleCount++;
        } else {
            card.style.display = 'none';
        }
    });

    // Update Counter
    const resultsCountEl = document.getElementById('resultsCount');
    if (resultsCountEl) {
        resultsCountEl.innerHTML = `<i class="fa-solid fa-compass"></i> <strong>${visibleCount}</strong> Iconic Treks`;
    }

    // Empty State Toggle
    const emptyState = document.getElementById('emptyState');
    const treksGrid = document.getElementById('treksGrid');
    if (emptyState) {
        if (visibleCount === 0) {
            emptyState.style.display = 'block';
            if (treksGrid) treksGrid.style.display = 'none';
        } else {
            emptyState.style.display = 'none';
            if (treksGrid) treksGrid.style.display = 'grid';
        }
    }

    // Sort Visible Cards
    sortCards(sortBy);
}

function sortCards(sortBy) {
    const grid = document.getElementById('treksGrid');
    if (!grid) return;

    const cardsArray = Array.from(grid.querySelectorAll('.trek-card'));

    cardsArray.sort((a, b) => {
        const altA = parseInt(a.getAttribute('data-altitude') || '0', 10);
        const altB = parseInt(b.getAttribute('data-altitude') || '0', 10);
        const daysA = parseInt(a.getAttribute('data-days') || '0', 10);
        const daysB = parseInt(b.getAttribute('data-days') || '0', 10);
        const ratA = parseFloat(a.getAttribute('data-rating') || '0');
        const ratB = parseFloat(b.getAttribute('data-rating') || '0');

        if (sortBy === 'altitude-desc') return altB - altA;
        if (sortBy === 'altitude-asc') return altA - altB;
        if (sortBy === 'duration-asc') return daysA - daysB;
        if (sortBy === 'duration-desc') return daysB - daysA;
        if (sortBy === 'rating') return ratB - ratA;
        return 0;
    });

    cardsArray.forEach(card => grid.appendChild(card));
}

function filterByRegion(region, element) {
    const regionSelect = document.getElementById('regionFilter');
    if (regionSelect) {
        regionSelect.value = region === 'all' ? 'all' : region;
        applyFilters();
    }
    
    // Update active mobile region pill if present
    if (element) {
        document.querySelectorAll('.mobile-region-pill').forEach(el => el.classList.remove('active'));
        element.classList.add('active');
    }
}

function filterBySeason(seasonName) {
    const seasonFilter = document.getElementById('seasonFilter');
    if (seasonFilter) {
        seasonFilter.value = seasonName;
        applyFilters();
    }
}

function syncMobileSearch(val) {
    const desktopInput = document.getElementById('searchFilter');
    if (desktopInput) {
        desktopInput.value = val;
    }
    applyFilters();
}

function filterByDifficultyQuick(diff, element) {
    const diffSelect = document.getElementById('difficultyFilter');
    if (diffSelect) {
        diffSelect.value = diff;
    }
    
    if (element) {
        document.querySelectorAll('.mobile-diff-chip').forEach(el => el.classList.remove('active'));
        element.classList.add('active');
    }
    
    applyFilters();
}

function scrollToTreksExplorer(event) {
    if (event) {
        event.preventDefault();
    }
    const section = document.getElementById('treksExplorerSection');
    if (section) {
        section.scrollIntoView({ behavior: 'smooth' });
    } else {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

function resetAllFilters() {
    const searchFilter = document.getElementById('searchFilter');
    const monthFilter = document.getElementById('monthFilter');
    const difficultyFilter = document.getElementById('difficultyFilter');
    const regionFilter = document.getElementById('regionFilter');
    const durationFilter = document.getElementById('durationFilter');
    const seasonFilter = document.getElementById('seasonFilter');
    const sortSelector = document.getElementById('sortSelector');

    if (searchFilter) searchFilter.value = '';
    if (monthFilter) monthFilter.value = 'all';
    if (difficultyFilter) difficultyFilter.value = 'all';
    if (regionFilter) regionFilter.value = 'all';
    if (durationFilter) durationFilter.value = 'all';
    if (seasonFilter) seasonFilter.value = 'all';
    if (sortSelector) sortSelector.value = 'featured';

    // Reset mobile search & chips
    const mobSearch = document.getElementById('mobileSearchInput');
    if (mobSearch) mobSearch.value = '';
    document.querySelectorAll('.mobile-region-pill').forEach((el, idx) => {
        el.classList.toggle('active', idx === 0);
    });
    document.querySelectorAll('.mobile-diff-chip').forEach((el, idx) => {
        el.classList.toggle('active', idx === 0);
    });

    applyFilters();
}

/* ==========================================
   Detailed Trek Modal
   ========================================== */
function openTrekModal(trekId) {
    const trek = allTreks.find(t => t.id === trekId);
    if (!trek) return;

    const modal = document.getElementById('trekDetailModal');
    const content = document.getElementById('trekModalContent');

    if (!modal || !content) return;

    const isSaved = savedTreks.includes(trek.id);

    // Clean duration parsing (No trailing slashes!)
    const durationParts = (trek.duration_text || '').split(' / ');
    const durationDays = durationParts[0] || `${trek.duration_days} Days`;
    const durationNights = durationParts[1] || '';

    // Clean Altitude parsing
    let altitudeFt = `${(trek.max_altitude_ft || 0).toLocaleString()} ft`;
    let altitudeM = '';
    if (trek.max_altitude_text && trek.max_altitude_text.includes('(')) {
        const match = trek.max_altitude_text.match(/^(.*?)\s*(\(.*?\))$/);
        if (match) {
            altitudeFt = match[1];
            altitudeM = match[2];
        }
    }

    content.innerHTML = `
        <div class="modal-mobile-drag-bar"></div>
        <div class="modal-trek-hero">
            <img src="${trek.image}" alt="${trek.name}" class="modal-hero-img">
            <div class="modal-hero-gradient-overlay"></div>
            
            <div class="modal-hero-top-bar">
                <div class="modal-hero-badges-group">
                    <span class="modal-badge-featured"><i class="fa-solid fa-award"></i> ${trek.badge}</span>
                    <span class="modal-badge-rating"><i class="fa-solid fa-star"></i> ${trek.rating} <span class="rating-sub">(${trek.reviews_count || 120} reviews)</span></span>
                </div>
                <button type="button" class="modal-close-round" onclick="closeTrekModal()" title="Close details">
                    <i class="fa-solid fa-xmark"></i>
                </button>
            </div>
        </div>

        <div class="modal-inner-content">
            <!-- Title & Location Header with Save Button on Right -->
            <div class="modal-title-header-block">
                <div class="modal-location-tags">
                    <span class="modal-tag-pill"><i class="fa-solid fa-location-dot"></i> ${trek.region}, ${trek.country}</span>
                    <span class="modal-tag-pill season-pill-tag"><i class="fa-regular fa-calendar-check"></i> ${trek.best_season}</span>
                    <span class="modal-tag-pill diff-pill-tag diff-${trek.difficulty_slug}"><i class="fa-solid fa-gauge-high"></i> ${trek.difficulty}</span>
                </div>
                <div class="modal-title-row">
                    <div class="modal-title-left">
                        <h2 class="modal-trek-title">${trek.name}</h2>
                        <p class="modal-trek-tagline">${trek.tagline}</p>
                    </div>
                    <button type="button" class="btn-modal-save-heart ${isSaved ? 'saved' : ''}" id="modalSaveBtn" onclick="toggleSaveTrek('${trek.id}')" title="${isSaved ? 'Remove from Saved Treks' : 'Save Trek to Wishlist'}">
                        <i class="${isSaved ? 'fa-solid fa-heart' : 'fa-regular fa-heart'}"></i>
                    </button>
                </div>
            </div>

            <!-- 4-Card Technical Metrics Grid -->
            <div class="modal-metrics-grid">
                <div class="modal-metric-card">
                    <div class="m-icon-wrap m-icon-time"><i class="fa-regular fa-clock"></i></div>
                    <div class="m-data">
                        <span class="m-label">Duration</span>
                        <strong class="m-val">${durationDays}</strong>
                        ${durationNights ? `<span class="m-sub-val">${durationNights}</span>` : ''}
                    </div>
                </div>
                <div class="modal-metric-card">
                    <div class="m-icon-wrap m-icon-distance"><i class="fa-solid fa-route"></i></div>
                    <div class="m-data">
                        <span class="m-label">Distance</span>
                        <strong class="m-val">${trek.distance_text || trek.distance_km + ' km'}</strong>
                        <span class="m-sub-val">Total Trail</span>
                    </div>
                </div>
                <div class="modal-metric-card">
                    <div class="m-icon-wrap m-icon-altitude"><i class="fa-solid fa-mountain"></i></div>
                    <div class="m-data">
                        <span class="m-label">Max Altitude</span>
                        <strong class="m-val">${altitudeFt}</strong>
                        ${altitudeM ? `<span class="m-sub-val">${altitudeM}</span>` : '<span class="m-sub-val">Summit Height</span>'}
                    </div>
                </div>
                <div class="modal-metric-card">
                    <div class="m-icon-wrap m-icon-diff"><i class="fa-solid fa-gauge-high"></i></div>
                    <div class="m-data">
                        <span class="m-label">Difficulty</span>
                        <strong class="m-val diff-color-${trek.difficulty_slug}">${trek.difficulty}</strong>
                        <span class="m-sub-val">Grading</span>
                    </div>
                </div>
            </div>

            <!-- Expedition Overview -->
            <div class="modal-section-card">
                <div class="modal-sec-header">
                    <span class="sec-icon sec-icon-purple"><i class="fa-solid fa-compass"></i></span>
                    <h4 class="modal-sec-title">Expedition Overview</h4>
                </div>
                <p class="modal-desc-text">${trek.description}</p>
            </div>

            <!-- Trail Highlights -->
            <div class="modal-section-card">
                <div class="modal-sec-header">
                    <span class="sec-icon sec-icon-amber"><i class="fa-solid fa-star"></i></span>
                    <h4 class="modal-sec-title">Key Highlights & Trail Features</h4>
                </div>
                <div class="modal-highlights-grid">
                    ${trek.highlights.map(h => `
                        <div class="highlight-pill-item">
                            <i class="fa-solid fa-circle-check"></i>
                            <span>${h}</span>
                        </div>
                    `).join('')}
                </div>
            </div>

            <!-- Logistics & Preparedness Bar -->
            <div class="modal-logistics-bar">
                <div class="logistics-item">
                    <span class="logistics-icon"><i class="fa-regular fa-calendar-days"></i></span>
                    <div class="logistics-text">
                        <span class="logistics-label">Best Months</span>
                        <strong class="logistics-val">${trek.best_months.join(', ')}</strong>
                    </div>
                </div>
                <div class="logistics-divider"></div>
                <div class="logistics-item">
                    <span class="logistics-icon"><i class="fa-solid fa-flag-checkered"></i></span>
                    <div class="logistics-text">
                        <span class="logistics-label">Basecamp / Start</span>
                        <strong class="logistics-val">${trek.start_point}</strong>
                    </div>
                </div>
                <div class="logistics-divider"></div>
                <div class="logistics-item">
                    <span class="logistics-icon"><i class="fa-solid fa-heart-pulse"></i></span>
                    <div class="logistics-text">
                        <span class="logistics-label">Fitness Level</span>
                        <strong class="logistics-val">${trek.fitness_level}</strong>
                    </div>
                </div>
            </div>

            <!-- Day-wise Expedition Itinerary & Campsite Altitudes -->
            ${trek.itinerary && trek.itinerary.length > 0 ? `
            <div class="modal-section-card modal-itinerary-card">
                <div class="modal-sec-header">
                    <span class="sec-icon sec-icon-teal"><i class="fa-solid fa-route"></i></span>
                    <div>
                        <h4 class="modal-sec-title">Day-wise Expedition Itinerary & Altitude Profile</h4>
                        <span class="modal-sec-subtitle">${trek.itinerary.length} Days Trail Route • Daily Campsites • Elevation Profile</span>
                    </div>
                </div>

                <div class="itinerary-timeline">
                    ${trek.itinerary.map(item => `
                        <div class="itinerary-day-row">
                            <div class="itinerary-day-badge">
                                <span class="itin-day-lbl">DAY</span>
                                <strong class="itin-day-num">${item.day}</strong>
                            </div>
                            <div class="itinerary-day-content">
                                <div class="itin-title-row">
                                    <h5 class="itin-title">${item.title}</h5>
                                </div>
                                <p class="itin-desc">${item.desc}</p>
                                <div class="itin-meta-tags">
                                    <div class="itin-tag-pill camp-tag" title="Night Campsite">
                                        <i class="fa-solid fa-campground"></i>
                                        <span class="tag-label">Campsite:</span>
                                        <strong class="tag-val">${item.campsite}</strong>
                                    </div>
                                    <div class="itin-tag-pill alt-tag" title="Elevation">
                                        <i class="fa-solid fa-mountain"></i>
                                        <span class="tag-label">Altitude:</span>
                                        <strong class="tag-val">${item.altitude}</strong>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
            ` : ''}
        </div>

        <!-- Modal Sticky Action Footer -->
        <div class="modal-footer-bar">
            <div class="modal-price-box">
                <span class="price-prefix">All-Inclusive Pass</span>
                <div class="price-main">
                    <strong class="modal-price-number">${trek.price}</strong>
                    <span class="price-tax">/ trekker</span>
                </div>
            </div>
            <div class="modal-action-btns">
                <a href="/treks/${trek.id}/guide" target="_blank" class="btn-modal-view-guide" title="View Official Expedition Guide & Itinerary in Browser">
                    <i class="fa-solid fa-arrow-up-right-from-square"></i> View Guide
                </a>
                <button type="button" class="btn-modal-download-pdf" id="btnDownloadPdf-${trek.id}" onclick="downloadTrekPdfGuide('${trek.id}', event)" title="Download Complete PDF Guide & Itinerary">
                    <i class="fa-solid fa-file-pdf"></i> Download PDF Guide
                </button>
                <button type="button" class="btn-modal-back-treks" onclick="closeTrekModal()">
                    <i class="fa-solid fa-arrow-left"></i> Back to Treks
                </button>
            </div>
        </div>
    `;

    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeTrekModal() {
    const modal = document.getElementById('trekDetailModal');
    if (modal) modal.classList.remove('active');
    document.body.style.overflow = '';
}

/* ==========================================
   Profile Dropdown Toggle
   ========================================== */
function toggleProfileMenu(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const menu = document.getElementById('profilePopoverMenu');
    const btn = document.getElementById('profileDropdownBtn');
    if (!menu) return;

    // Close chatbot popover if open
    const chatbotPopover = document.getElementById('chatbotPopover');
    const chatbotBtn = document.getElementById('trekChatbotBtn');
    if (chatbotPopover && chatbotPopover.classList.contains('show')) {
        chatbotPopover.classList.remove('show');
        if (chatbotBtn) chatbotBtn.classList.remove('active');
    }

    // Close checklist popover if open
    const checklistPopover = document.getElementById('checklistPopover');
    const checklistBtn = document.getElementById('trekChecklistBtn');
    if (checklistPopover && checklistPopover.classList.contains('show')) {
        checklistPopover.classList.remove('show');
        if (checklistBtn) checklistBtn.classList.remove('active');
    }

    // Close saved treks popover if open
    const savedPopover = document.getElementById('savedTreksPopover');
    const savedBtn = document.getElementById('savedTreksBtn');
    if (savedPopover && savedPopover.classList.contains('show')) {
        savedPopover.classList.remove('show');
        if (savedBtn) savedBtn.classList.remove('active');
    }

    const isShown = menu.classList.contains('show');
    if (isShown) {
        menu.classList.remove('show');
        if (btn) btn.classList.remove('active');
    } else {
        menu.classList.add('show');
        if (btn) btn.classList.add('active');
    }
}

/* ==========================================
   Trek Packing Checklist / Essentials Manager
   ========================================== */
const DEFAULT_CHECKLIST_ITEMS = [
    // Gear
    { id: 'chk-gear-1', name: 'Rucksack / Backpack (40L - 60L)', category: 'gear', tip: 'With rain cover & supportive hip belt', default: true },
    { id: 'chk-gear-2', name: 'Trekking Shoes (High Ankle Support)', category: 'gear', tip: 'Water-resistant with deep lugs & firm grip', default: true },
    { id: 'chk-gear-3', name: 'Trekking Poles (1 Pair)', category: 'gear', tip: 'Shock-absorbent, height adjustable to save knees', default: true },
    { id: 'chk-gear-4', name: 'Headlamp / Torch with Extra Batteries', category: 'gear', tip: 'Crucial for night walks and early summit push', default: true },
    { id: 'chk-gear-5', name: 'Rain Poncho / Seam-Sealed Raincoat', category: 'gear', tip: 'Protection against sudden mountain showers & wind', default: true },
    { id: 'chk-gear-6', name: 'UV400 Polarized Sunglasses (Cat 3/4)', category: 'gear', tip: 'Prevents snow blindness and harmful high-altitude UV', default: true },

    // Clothing
    { id: 'chk-cloth-1', name: 'Thermal Inners (Top & Bottom)', category: 'clothing', tip: '1-2 pairs (Merino wool or warm moisture-wicking synthetic)', default: true },
    { id: 'chk-cloth-2', name: 'Warm Fleece & Down/Puffer Jacket', category: 'clothing', tip: 'Rated for -5°C to -10°C for high campsites', default: true },
    { id: 'chk-cloth-3', name: 'Quick-Dry Trekking T-shirts (2-3 Pairs)', category: 'clothing', tip: 'Full sleeve, breathable & anti-odor fabric', default: true },
    { id: 'chk-cloth-4', name: 'Water-Resistant Trek Pants (2 Pairs)', category: 'clothing', tip: 'Quick-dry stretch fabric with secure zip pockets', default: true },
    { id: 'chk-cloth-5', name: 'Padded Woolen Socks (2-3 Pairs)', category: 'clothing', tip: 'Plus 2 pairs regular synthetic liner socks', default: true },
    { id: 'chk-cloth-6', name: 'Waterproof Outer Gloves & Fleece Inners', category: 'clothing', tip: 'Dual-layer protection against cold and frostbite', default: true },
    { id: 'chk-cloth-7', name: 'Woolen Beanie & UV Sun Protection Cap', category: 'clothing', tip: 'Cover head and ears from cold wind and daytime sun', default: true },

    // Medical
    { id: 'chk-med-1', name: 'Diamox (Acetazolamide - Altitude AMS)', category: 'medical', tip: 'Consult your doctor before consumption', default: true },
    { id: 'chk-med-2', name: 'Personal First-Aid & Pain Relief Kit', category: 'medical', tip: 'Paracetamol, Ibuprofen, Band-Aids, Crape bandage', default: true },
    { id: 'chk-med-3', name: 'ORS & Electrolyte Energy Sachets', category: 'medical', tip: 'Mix with water daily to prevent dehydration & cramps', default: true },
    { id: 'chk-med-4', name: 'Blister Tape / Anti-Friction Pads', category: 'medical', tip: 'Immediate heel and toe friction relief', default: true },

    // Docs & Tools
    { id: 'chk-tool-1', name: 'Original Govt ID Proof & Medical Certificate', category: 'essentials', tip: 'Aadhaar / Passport for forest checkposts & permits', default: true },
    { id: 'chk-tool-2', name: 'Power Bank (10,000 - 20,000 mAh)', category: 'essentials', tip: 'Cold drains phone battery rapidly; keep in inner pocket', default: true },
    { id: 'chk-tool-3', name: 'Insulated Thermos / Water Bottle (1L - 2L)', category: 'essentials', tip: 'Retains warm water throughout the day', default: true },
    { id: 'chk-tool-4', name: 'Sunscreen SPF 50+ & Hydrating Lip Balm', category: 'essentials', tip: 'UV radiation is 40% higher above tree-line', default: true },
    { id: 'chk-tool-5', name: 'Quick-Dry Microfiber Towel & Wet Wipes', category: 'essentials', tip: 'Lightweight, compact hygiene essentials', default: true }
];

let checklistItems = [];
let checkedItemIds = new Set();
let activeChecklistCategory = 'all';

function initChecklist() {
    const savedItems = localStorage.getItem('amu_trek_checklist_items');
    if (savedItems !== null) {
        try {
            checklistItems = JSON.parse(savedItems);
        } catch (e) {
            checklistItems = [...DEFAULT_CHECKLIST_ITEMS];
        }
    } else {
        checklistItems = [...DEFAULT_CHECKLIST_ITEMS];
        localStorage.setItem('amu_trek_checklist_items', JSON.stringify(checklistItems));
    }

    const savedChecked = localStorage.getItem('amu_trek_checklist_checked');
    if (savedChecked) {
        try {
            const arr = JSON.parse(savedChecked);
            checkedItemIds = new Set(arr);
        } catch (e) {
            checkedItemIds = new Set();
        }
    } else {
        checkedItemIds = new Set();
    }

    // Prevent clicks inside popover from closing it
    const pop = document.getElementById('checklistPopover');
    if (pop) {
        pop.addEventListener('click', (e) => {
            e.stopPropagation();
        });
    }

    renderChecklist();
}

function saveChecklistState() {
    localStorage.setItem('amu_trek_checklist_checked', JSON.stringify(Array.from(checkedItemIds)));
    localStorage.setItem('amu_trek_checklist_items', JSON.stringify(checklistItems));
    updateChecklistUI();
}

function toggleChecklistItem(itemId, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }

    const isCurrentlyChecked = checkedItemIds.has(itemId);
    if (isCurrentlyChecked) {
        checkedItemIds.delete(itemId);
    } else {
        checkedItemIds.add(itemId);
    }
    saveChecklistState();

    // Directly update target DOM element for smooth state toggle without scroll jumping
    const itemEl = document.getElementById(`chk-item-${itemId}`);
    if (itemEl) {
        const isChecked = checkedItemIds.has(itemId);
        if (isChecked) {
            itemEl.classList.add('checked');
        } else {
            itemEl.classList.remove('checked');
        }
        const box = itemEl.querySelector('.checklist-checkbox-custom');
        if (box) {
            box.innerHTML = isChecked ? '<i class="fa-solid fa-check"></i>' : '';
        }
    } else {
        renderChecklistItemsOnly();
    }
}

function checkAllChecklistItems(event) {
    if (event) event.stopPropagation();
    checklistItems.forEach(item => checkedItemIds.add(item.id));
    saveChecklistState();
    renderChecklistItemsOnly();
}

function resetChecklistItems(event) {
    if (event) event.stopPropagation();
    checkedItemIds.clear();
    saveChecklistState();
    renderChecklistItemsOnly();
}

function restoreDefaultChecklistItems(event) {
    if (event) event.stopPropagation();
    if (confirm('Restore all default trekking essentials back to your checklist?')) {
        const customItems = checklistItems.filter(i => !i.default);
        // Merge defaults with any unique custom items
        checklistItems = [...DEFAULT_CHECKLIST_ITEMS, ...customItems];
        saveChecklistState();
        renderChecklist();
    }
}

function filterChecklistCategory(cat, btn, event) {
    if (event) event.stopPropagation();
    activeChecklistCategory = cat;
    document.querySelectorAll('.checklist-tab').forEach(t => t.classList.remove('active'));
    if (btn) btn.classList.add('active');
    renderChecklistItemsOnly();
}

function addCustomChecklistItem(event) {
    if (event) event.stopPropagation();
    const input = document.getElementById('customChecklistInput');
    if (!input) return;
    const val = input.value.trim();
    if (!val) return;

    const newItem = {
        id: 'chk-custom-' + Date.now(),
        name: val,
        category: activeChecklistCategory === 'all' ? 'gear' : activeChecklistCategory,
        tip: 'Custom personal item',
        default: false
    };

    checklistItems.push(newItem);
    input.value = '';
    saveChecklistState();
    renderChecklist();
}

function removeChecklistItem(itemId, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    checklistItems = checklistItems.filter(i => i.id !== itemId);
    checkedItemIds.delete(itemId);
    saveChecklistState();
    renderChecklist();
}

function updateChecklistUI() {
    const total = checklistItems.length;
    const packed = checklistItems.filter(item => checkedItemIds.has(item.id)).length;
    const pct = total > 0 ? Math.round((packed / total) * 100) : 0;

    // 1. Update Progress stats in popover
    const progText = document.getElementById('checklistProgressText');
    if (progText) {
        progText.innerHTML = `<i class="fa-solid fa-box-open"></i> Packed: <strong>${packed}</strong> of <strong>${total}</strong>`;
    }

    const progPct = document.getElementById('checklistProgressPct');
    if (progPct) {
        progPct.textContent = `${pct}%`;
    }

    const progFill = document.getElementById('checklistProgressFill');
    if (progFill) {
        progFill.style.width = `${pct}%`;
    }

    // 3. Update tab total count
    const tabAllCount = document.getElementById('count-tab-all');
    if (tabAllCount) {
        tabAllCount.textContent = total;
    }
}

function renderChecklistItemsOnly() {
    const listEl = document.getElementById('checklistItemsList');
    if (!listEl) return;

    const filtered = activeChecklistCategory === 'all' 
        ? checklistItems 
        : checklistItems.filter(i => i.category === activeChecklistCategory);

    if (filtered.length === 0) {
        listEl.innerHTML = `
            <div style="text-align: center; padding: 24px 10px; color: var(--text-muted); font-size: 0.8rem;">
                <i class="fa-solid fa-clipboard-question" style="font-size: 1.8rem; opacity: 0.4; margin-bottom: 6px; display: block;"></i>
                No items in this category yet.
            </div>
        `;
        return;
    }

    listEl.innerHTML = filtered.map(item => {
        const isChecked = checkedItemIds.has(item.id);
        const catBadge = item.category.toUpperCase();
        const safeName = item.name.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
        return `
            <div class="checklist-item ${isChecked ? 'checked' : ''}" id="chk-item-${item.id}" onclick="toggleChecklistItem('${item.id}', event)">
                <div class="checklist-checkbox-custom">
                    ${isChecked ? '<i class="fa-solid fa-check"></i>' : ''}
                </div>
                <div class="checklist-item-content">
                    <div class="checklist-item-header-row">
                        <span class="checklist-item-name">${item.name}</span>
                        <div class="checklist-item-header-actions">
                            <span class="checklist-item-badge">${catBadge}</span>
                            <button type="button" class="btn-remove-checklist-item" onclick="removeChecklistItem('${item.id}', event)" title="Delete '${safeName}'">
                                <i class="fa-regular fa-trash-can"></i>
                            </button>
                        </div>
                    </div>
                    ${item.tip ? `<span class="checklist-item-tip">${item.tip}</span>` : ''}
                </div>
            </div>
        `;
    }).join('');
}

function renderChecklist() {
    updateChecklistUI();
    renderChecklistItemsOnly();
}

/* ==========================================
   AI Trek Guide Chatbot Controller (Sherpa AI)
   ========================================== */
let chatbotMessages = [
    {
        sender: 'bot',
        text: "Namaste! 🏔️ I am **Sherpa AI**, your personal mountain guide for **Trekkers Heaven**.\n\nAsk me about:\n• Best beginner or budget treks\n• High-altitude safety & AMS prevention\n• Packing essentials & gear advice\n• Day-wise itineraries & mountain passes",
        time: formatChatTime(new Date()),
        suggestions: ["Best beginner treks?", "How to prevent AMS?", "Winter snow treks", "Gear packing tips"]
    }
];

function formatChatTime(date) {
    const d = date || new Date();
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function initChatbot() {
    const savedChat = sessionStorage.getItem('th_chatbot_history');
    if (savedChat) {
        try {
            chatbotMessages = JSON.parse(savedChat);
        } catch (e) {}
    }

    // Stop popover clicks from closing it
    const pop = document.getElementById('chatbotPopover');
    if (pop) {
        pop.addEventListener('click', (e) => {
            e.stopPropagation();
        });
    }

    renderChatbotMessages();
}

function saveChatbotHistory() {
    sessionStorage.setItem('th_chatbot_history', JSON.stringify(chatbotMessages));
}

function clearChatbotHistory(event) {
    if (event) event.stopPropagation();
    chatbotMessages = [
        {
            sender: 'bot',
            text: "Chat cleared! 🏔️ How can I help you plan your next mountain journey?",
            time: formatChatTime(new Date()),
            suggestions: ["Best beginner treks?", "Treks under ₹10,000", "Packing essentials", "AMS prevention"]
        }
    ];
    saveChatbotHistory();
    renderChatbotMessages();
}

function renderChatbotMessages() {
    const body = document.getElementById('chatbotMessagesBody');
    if (!body) return;

    body.innerHTML = chatbotMessages.map(msg => {
        const isUser = msg.sender === 'user';
        const formattedHtml = formatChatMarkdown(msg.text);
        
        let actionsHtml = '';
        if (msg.trekId) {
            actionsHtml = `
                <div class="chat-trek-card-action" onclick="openTrekModal('${msg.trekId}'); toggleChatbotPopover();">
                    <span><i class="fa-solid fa-mountain-sun"></i> View <strong>${msg.trekName || 'Trek Details'}</strong></span>
                    <i class="fa-solid fa-arrow-right"></i>
                </div>
            `;
        } else if (msg.compareTreks && Array.isArray(msg.compareTreks) && msg.compareTreks.length >= 2) {
            actionsHtml = `
                <div class="chat-compare-actions">
                    <button type="button" class="chat-compare-btn" onclick="openTrekModal('${msg.compareTreks[0].id}'); toggleChatbotPopover();" title="View ${msg.compareTreks[0].name}">
                        <i class="fa-solid fa-mountain-sun"></i> ${msg.compareTreks[0].name.replace(' Trek', '')}
                    </button>
                    <button type="button" class="chat-compare-btn" onclick="openTrekModal('${msg.compareTreks[1].id}'); toggleChatbotPopover();" title="View ${msg.compareTreks[1].name}">
                        <i class="fa-solid fa-mountain-sun"></i> ${msg.compareTreks[1].name.replace(' Trek', '')}
                    </button>
                </div>
            `;
        }

        return `
            <div class="chat-msg ${isUser ? 'user' : 'bot'}">
                <div class="chat-bubble ${isUser ? 'user' : 'bot'}">
                    ${formattedHtml}
                    ${actionsHtml}
                </div>
                <span class="chat-time">${msg.time || ''}</span>
            </div>
        `;
    }).join('');

    // Scroll to bottom
    body.scrollTop = body.scrollHeight;
}

function formatChatMarkdown(text) {
    if (!text) return '';
    let html = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Headings (### Heading, ## Heading, # Heading)
    html = html.replace(/^###\s+(.*$)/gim, '<h5 style="margin: 8px 0 4px 0; font-size: 0.92rem; font-weight: 800; color: #c4b5fd;">$1</h5>');
    html = html.replace(/^##\s+(.*$)/gim, '<h4 style="margin: 10px 0 4px 0; font-size: 1rem; font-weight: 800; color: #ffffff;">$1</h4>');
    html = html.replace(/^#\s+(.*$)/gim, '<h3 style="margin: 12px 0 6px 0; font-size: 1.08rem; font-weight: 800; color: #ffffff;">$1</h3>');

    // Bold **text**
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Italic *text*
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Markdown bullet lists (- item or * item)
    html = html.replace(/^\s*[-*]\s+(.*$)/gim, '• $1');

    // Line breaks
    html = html.replace(/\n/g, '<br>');
    return html;
}

function toggleChatbotPopover(event) {
    if (event && typeof event.stopPropagation === 'function') event.stopPropagation();
    const popover = document.getElementById('chatbotPopover');
    const btn = document.getElementById('trekChatbotBtn');
    if (!popover) return;

    // Close other popovers if open
    const checklistPopover = document.getElementById('checklistPopover');
    const checklistBtn = document.getElementById('trekChecklistBtn');
    if (checklistPopover && checklistPopover.classList.contains('show')) {
        checklistPopover.classList.remove('show');
        if (checklistBtn) checklistBtn.classList.remove('active');
    }

    const savedPopover = document.getElementById('savedTreksPopover');
    const savedBtn = document.getElementById('savedTreksBtn');
    if (savedPopover && savedPopover.classList.contains('show')) {
        savedPopover.classList.remove('show');
        if (savedBtn) savedBtn.classList.remove('active');
    }

    const profileMenu = document.getElementById('profilePopoverMenu');
    const profileBtn = document.getElementById('profileDropdownBtn');
    if (profileMenu && profileMenu.classList.contains('show')) {
        profileMenu.classList.remove('show');
        if (profileBtn) profileBtn.classList.remove('active');
    }

    const isShown = popover.classList.contains('show');
    if (isShown) {
        popover.classList.remove('show');
        if (btn) btn.classList.remove('active');
    } else {
        popover.classList.add('show');
        if (btn) btn.classList.add('active');
        // Focus input
        setTimeout(() => {
            const input = document.getElementById('chatbotInput');
            if (input) input.focus();
            const body = document.getElementById('chatbotMessagesBody');
            if (body) body.scrollTop = body.scrollHeight;
        }, 100);
    }
}

function handleChatbotChipClick(promptText, event) {
    if (event && typeof event.stopPropagation === 'function') event.stopPropagation();
    const input = document.getElementById('chatbotInput');
    if (input) {
        input.value = promptText;
        sendChatbotMessage();
    }
}

async function sendChatbotMessage(event) {
    if (event && typeof event.preventDefault === 'function') {
        event.preventDefault();
    }
    if (event && typeof event.stopPropagation === 'function') {
        event.stopPropagation();
    }
    const input = document.getElementById('chatbotInput');
    if (!input) return;
    const text = input.value.trim();
    if (!text) return;

    // Build history for multi-turn context (last 6 messages)
    const historyPayload = chatbotMessages.slice(-6).map(m => ({
        role: m.sender === 'user' ? 'user' : 'model',
        text: m.text
    }));

    // Append user message
    chatbotMessages.push({
        sender: 'user',
        text: text,
        time: formatChatTime(new Date())
    });
    input.value = '';
    saveChatbotHistory();
    renderChatbotMessages();

    // Show typing indicator
    const body = document.getElementById('chatbotMessagesBody');
    const typingEl = document.createElement('div');
    typingEl.className = 'chat-msg bot';
    typingEl.id = 'chatTypingIndicator';
    typingEl.innerHTML = `
        <div class="chat-typing-dots">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;
    if (body) {
        body.appendChild(typingEl);
        body.scrollTop = body.scrollHeight;
    }

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                message: text,
                history: historyPayload
            })
        });
        const data = await res.json();

        // Remove typing indicator
        const ind = document.getElementById('chatTypingIndicator');
        if (ind) ind.remove();

        chatbotMessages.push({
            sender: 'bot',
            text: data.reply || "I am currently taking a breather at base camp. Please ask again!",
            trekId: data.trek_id,
            trekName: data.trek_name,
            compareTreks: data.compare_treks,
            time: formatChatTime(new Date())
        });
        saveChatbotHistory();
        renderChatbotMessages();

        // Update suggestion chips dynamically if provided
        if (data.suggestions && Array.isArray(data.suggestions) && data.suggestions.length > 0) {
            updateChatbotSuggestions(data.suggestions);
        }
    } catch (err) {
        const ind = document.getElementById('chatTypingIndicator');
        if (ind) ind.remove();

        chatbotMessages.push({
            sender: 'bot',
            text: "⚠️ Unable to connect to Sherpa AI servers right now. Please check your internet connection.",
            time: formatChatTime(new Date())
        });
        saveChatbotHistory();
        renderChatbotMessages();
    }
}

function updateChatbotSuggestions(suggestions) {
    const wrap = document.getElementById('chatbotSuggestionsWrap');
    if (!wrap) return;
    wrap.innerHTML = suggestions.map(s => `
        <button type="button" class="chatbot-chip" onclick="handleChatbotChipClick('${s.replace(/'/g, "\\'")}', event)">
            <i class="fa-solid fa-sparkles"></i> ${s}
        </button>
    `).join('');
}

function toggleChecklistPopover(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const popover = document.getElementById('checklistPopover');
    const btn = document.getElementById('trekChecklistBtn');
    if (!popover) return;

    // Close chatbot popover if open
    const chatPopover = document.getElementById('chatbotPopover');
    const chatBtn = document.getElementById('trekChatbotBtn');
    if (chatPopover && chatPopover.classList.contains('show')) {
        chatPopover.classList.remove('show');
        if (chatBtn) chatBtn.classList.remove('active');
    }

    // Close saved popover if open
    const savedPopover = document.getElementById('savedTreksPopover');
    const savedBtn = document.getElementById('savedTreksBtn');
    if (savedPopover && savedPopover.classList.contains('show')) {
        savedPopover.classList.remove('show');
        if (savedBtn) savedBtn.classList.remove('active');
    }

    // Close profile popover if open
    const profileMenu = document.getElementById('profilePopoverMenu');
    const profileBtn = document.getElementById('profileDropdownBtn');
    if (profileMenu && profileMenu.classList.contains('show')) {
        profileMenu.classList.remove('show');
        if (profileBtn) profileBtn.classList.remove('active');
    }

    const isShown = popover.classList.contains('show');
    if (isShown) {
        popover.classList.remove('show');
        if (btn) btn.classList.remove('active');
    } else {
        popover.classList.add('show');
        if (btn) btn.classList.add('active');
    }
}

// Close popovers when clicking outside (safe for mobile bottom nav)
document.addEventListener('click', (e) => {
    // If click was inside mobile bottom nav or drawer headers, do not close
    if (e.target.closest('#mobileBottomNav') || e.target.closest('.mobile-bottom-nav')) {
        return;
    }

    // Chatbot Popover
    const chatbotPopover = document.getElementById('chatbotPopover');
    const chatbotBtn = document.getElementById('trekChatbotBtn');
    if (chatbotPopover && chatbotPopover.classList.contains('show')) {
        if (!chatbotPopover.contains(e.target) && !chatbotBtn?.contains(e.target)) {
            chatbotPopover.classList.remove('show');
            if (chatbotBtn) chatbotBtn.classList.remove('active');
        }
    }

    // Checklist Popover
    const checklistPopover = document.getElementById('checklistPopover');
    const checklistBtn = document.getElementById('trekChecklistBtn');
    if (checklistPopover && checklistPopover.classList.contains('show')) {
        if (!checklistPopover.contains(e.target) && !checklistBtn?.contains(e.target)) {
            checklistPopover.classList.remove('show');
            if (checklistBtn) checklistBtn.classList.remove('active');
        }
    }

    // Profile Popover
    const profileMenu = document.getElementById('profilePopoverMenu');
    const profileBtn = document.getElementById('profileDropdownBtn');
    if (profileMenu && profileMenu.classList.contains('show')) {
        if (!profileMenu.contains(e.target) && !profileBtn?.contains(e.target)) {
            profileMenu.classList.remove('show');
            if (profileBtn) profileBtn.classList.remove('active');
        }
    }

    // Saved Treks Popover
    const savedPopover = document.getElementById('savedTreksPopover');
    const savedBtn = document.getElementById('savedTreksBtn');
    if (savedPopover && savedPopover.classList.contains('show')) {
        if (!savedPopover.contains(e.target) && !savedBtn?.contains(e.target)) {
            savedPopover.classList.remove('show');
            if (savedBtn) savedBtn.classList.remove('active');
        }
    }
});

function toggleMobileFilterDrawer(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const sidebar = document.getElementById('sidebarFilters');
    if (!sidebar) return;

    // Close any open popovers
    ['chatbotPopover', 'checklistPopover', 'savedTreksPopover', 'profilePopoverMenu'].forEach(id => {
        const p = document.getElementById(id);
        if (p) p.classList.remove('show');
    });

    sidebar.classList.toggle('mobile-drawer-open');
    let backdrop = document.getElementById('filterDrawerBackdrop');
    if (!backdrop) {
        backdrop = document.createElement('div');
        backdrop.id = 'filterDrawerBackdrop';
        backdrop.className = 'filter-drawer-backdrop';
        backdrop.onclick = () => {
            sidebar.classList.remove('mobile-drawer-open');
            backdrop.remove();
        };
        document.body.appendChild(backdrop);
    }
    if (!sidebar.classList.contains('mobile-drawer-open')) {
        backdrop.remove();
    }
}

function handleProfileNavClick(event, isLoggedIn) {
    if (!isLoggedIn) {
        if (event) event.preventDefault();
        window.location.href = '/login';
    }
}

/* ==========================================
   Toast Notification Helper for Treks Page
   ========================================== */
function showToast(message, type = 'info') {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type} show`;

    let iconClass = 'fa-solid fa-circle-info';
    if (type === 'success') iconClass = 'fa-solid fa-circle-check';
    else if (type === 'danger') iconClass = 'fa-solid fa-circle-xmark';
    else if (type === 'warning') iconClass = 'fa-solid fa-triangle-exclamation';

    toast.innerHTML = `
        <div class="toast-icon"><i class="${iconClass}"></i></div>
        <div class="toast-text">${message}</div>
        <button class="toast-close">&times;</button>
    `;

    toast.querySelector('.toast-close').addEventListener('click', () => {
        toast.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-10px)';
        setTimeout(() => toast.remove(), 200);
    });

    container.appendChild(toast);

    setTimeout(() => {
        if (toast && toast.parentElement) {
            toast.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(-10px)';
            setTimeout(() => toast.remove(), 250);
        }
    }, 3200);
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/[&<>"']/g, function(m) {
        return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[m];
    });
}

/* ==========================================
   Downloadable PDF Trek Guide & Itinerary Generator
   ========================================== */
async function downloadTrekPdfGuide(trekId, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }

    const trek = allTreks.find(t => t.id === trekId);
    if (!trek) return;

    const btn = document.getElementById(`btnDownloadPdf-${trek.id}`) || event?.currentTarget;
    const originalContent = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generating PDF...';
    }

    showToast(`Preparing Expedition Guide for ${trek.name}...`, 'info');

    try {
        // Fetch full rich guide data (including official permits & emergency SOS)
        let guideData = null;
        try {
            const res = await fetch(`/api/treks/${trek.id}/guide`);
            if (res.ok) {
                const data = await res.json();
                if (data.success) {
                    guideData = data;
                }
            }
        } catch (e) {
            console.warn('Could not fetch guide endpoint, using local fallback:', e);
        }

        const permits = guideData?.permits || {
            permits_required: [
                'State Forest Department Transit & Camping Permit',
                'Local Wildlife Sanctuary / Environmental Entry Pass'
            ],
            documents_needed: [
                'Original Government Photo ID Proof (Aadhaar / Passport / Voter ID) + 2 photocopies',
                'Medical Fitness Certificate signed by a certified MBBS doctor',
                'Trekker Disclaimer & Indemnity Undertaking Form'
            ],
            fee_details: 'Approx. ₹150–₹350 per day (Forest & Sanctuary entry fees)',
            issuing_office: `${trek.start_point || 'Basecamp'} Forest Checkpost Gate`
        };

        const emergencySos = guideData?.emergency_sos || {
            helpline_india: '112 / 1070 (Disaster Management)',
            sdrf_uttarakhand: '+91-135-2710334 / 1070',
            sdrf_himachal: '+91-177-2812344 / 1070',
            jk_rescue: '+91-194-2452138 / 100',
            ladakh_rescue: '+91-1982-255588',
            nepal_rescue: '+977-1-4247041 / 100',
            ambulance: '108',
            medical_guideline: 'Never ascend with AMS symptoms. Inform trek leader immediately.'
        };

        // Build cleanly styled PDF printable element
        const printContainer = document.createElement('div');
        printContainer.id = 'trekPdfExportContainer';
        printContainer.style.cssText = `
            width: 794px;
            padding: 32px 36px;
            background: #ffffff;
            color: #0f172a;
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.5;
            box-sizing: border-box;
            position: absolute;
            left: -9999px;
            top: 0;
        `;

        // Duration formatting
        const durationParts = (trek.duration_text || '').split(' / ');
        const durationDays = durationParts[0] || `${trek.duration_days} Days`;
        const durationNights = durationParts[1] || `${(trek.duration_days || 1) - 1} Nights`;

        // Altitude formatting
        const altitudeText = trek.max_altitude_text || `${(trek.max_altitude_ft || 0).toLocaleString()} ft`;

        // Itinerary rows HTML
        let itineraryRowsHtml = '';
        if (trek.itinerary && trek.itinerary.length > 0) {
            itineraryRowsHtml = trek.itinerary.map(item => `
                <tr style="border-bottom: 1px solid #e2e8f0;">
                    <td style="padding: 9px 8px; font-weight: 800; color: #6366f1; vertical-align: top; width: 62px; font-size: 11px;">
                        DAY ${item.day}
                    </td>
                    <td style="padding: 9px 8px; vertical-align: top;">
                        <strong style="font-size: 12px; color: #0f172a; display: block; margin-bottom: 2px;">${escapeHtml(item.title)}</strong>
                        <span style="font-size: 11px; color: #475569; display: block; line-height: 1.4;">${escapeHtml(item.desc)}</span>
                    </td>
                    <td style="padding: 9px 8px; vertical-align: top; width: 140px; font-size: 11px; color: #334155;">
                        <strong style="display: block; color: #0f172a; font-size: 11px;">⛺ ${escapeHtml(item.campsite)}</strong>
                        <span style="color: #64748b; font-size: 10px;">▲ ${escapeHtml(item.altitude)}</span>
                    </td>
                </tr>
            `).join('');
        } else {
            itineraryRowsHtml = `
                <tr>
                    <td colspan="3" style="padding: 14px; text-align: center; color: #64748b; font-size: 12px;">
                        Standard high-altitude guided expedition route.
                    </td>
                </tr>
            `;
        }

        // Permits bullets
        const permitsHtml = permits.permits_required.map(p => `<li style="margin-bottom: 4px; font-size: 11px; color: #334155;">${escapeHtml(p)}</li>`).join('');
        const docsHtml = permits.documents_needed.map(d => `<li style="margin-bottom: 4px; font-size: 11px; color: #334155;">${escapeHtml(d)}</li>`).join('');

        // Highlights
        const highlightsHtml = (trek.highlights || []).map(h => `
            <div style="background: #f1f5f9; border-radius: 6px; padding: 6px 10px; font-size: 11px; font-weight: 600; color: #1e293b; display: flex; align-items: center; gap: 6px;">
                <span style="color: #10b981;">✓</span> ${escapeHtml(h)}
            </div>
        `).join('');

        printContainer.innerHTML = `
            <!-- Top Branded Header -->
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #6366f1; padding-bottom: 14px; margin-bottom: 18px;">
                <div>
                    <div style="font-size: 18px; font-weight: 900; letter-spacing: -0.5px; color: #0f172a; display: flex; align-items: center; gap: 6px;">
                        <span>TREKKERS</span><span style="color: #6366f1;">HEAVEN</span>
                    </div>
                    <span style="font-size: 10px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.8px;">Official Expedition Field Guide & Detailed Itinerary</span>
                </div>
                <div style="text-align: right;">
                    <span style="background: #e0e7ff; color: #4338ca; font-size: 10px; font-weight: 800; padding: 4px 10px; border-radius: 20px; text-transform: uppercase; letter-spacing: 0.5px;">
                        ${escapeHtml(trek.badge || 'Himalayan Classic')}
                    </span>
                    <div style="font-size: 11px; color: #64748b; font-weight: 600; margin-top: 3px;">⭐ ${trek.rating || '4.9'} / 5.0 Rating</div>
                </div>
            </div>

            <!-- Trek Title & Region Banner -->
            <div style="background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); color: #ffffff; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px;">
                <span style="font-size: 11px; font-weight: 700; color: #a5b4fc; text-transform: uppercase; letter-spacing: 0.6px; display: block; margin-bottom: 4px;">
                    📍 ${escapeHtml(trek.region)}, ${escapeHtml(trek.country)}
                </span>
                <h1 style="font-size: 22px; font-weight: 800; margin: 0 0 6px 0; letter-spacing: -0.4px; color: #ffffff;">
                    ${escapeHtml(trek.name)}
                </h1>
                <p style="font-size: 12px; color: #c7d2fe; margin: 0; line-height: 1.4;">
                    ${escapeHtml(trek.tagline || trek.description || '')}
                </p>
            </div>

            <!-- Key Technical Metrics Grid (6 Boxes) -->
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 18px;">
                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 12px;">
                    <span style="font-size: 10px; color: #64748b; font-weight: 700; text-transform: uppercase; display: block; margin-bottom: 2px;">Max Altitude</span>
                    <strong style="font-size: 14px; color: #0f172a; font-weight: 800;">${escapeHtml(altitudeText)}</strong>
                </div>
                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 12px;">
                    <span style="font-size: 10px; color: #64748b; font-weight: 700; text-transform: uppercase; display: block; margin-bottom: 2px;">Total Duration</span>
                    <strong style="font-size: 14px; color: #0f172a; font-weight: 800;">${escapeHtml(durationDays)} (${escapeHtml(durationNights)})</strong>
                </div>
                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 12px;">
                    <span style="font-size: 10px; color: #64748b; font-weight: 700; text-transform: uppercase; display: block; margin-bottom: 2px;">Trail Distance</span>
                    <strong style="font-size: 14px; color: #0f172a; font-weight: 800;">${escapeHtml(trek.distance_text || trek.distance_km + ' km')}</strong>
                </div>
                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 12px;">
                    <span style="font-size: 10px; color: #64748b; font-weight: 700; text-transform: uppercase; display: block; margin-bottom: 2px;">Difficulty Level</span>
                    <strong style="font-size: 13px; color: #6366f1; font-weight: 800;">${escapeHtml(trek.difficulty)} (${escapeHtml(trek.fitness_level || 'Fit')})</strong>
                </div>
                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 12px;">
                    <span style="font-size: 10px; color: #64748b; font-weight: 700; text-transform: uppercase; display: block; margin-bottom: 2px;">Best Season</span>
                    <strong style="font-size: 13px; color: #0f172a; font-weight: 800;">${escapeHtml(trek.best_season || 'All Season')}</strong>
                </div>
                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 12px;">
                    <span style="font-size: 10px; color: #64748b; font-weight: 700; text-transform: uppercase; display: block; margin-bottom: 2px;">Basecamp / Trailhead</span>
                    <strong style="font-size: 12px; color: #0f172a; font-weight: 800;">${escapeHtml(trek.start_point || 'Basecamp')}</strong>
                </div>
            </div>

            <!-- Expedition Overview -->
            <div style="margin-bottom: 18px;">
                <h3 style="font-size: 13px; font-weight: 800; text-transform: uppercase; color: #1e293b; letter-spacing: 0.5px; margin: 0 0 6px 0; border-left: 3px solid #6366f1; padding-left: 8px;">
                    Expedition Overview
                </h3>
                <p style="font-size: 11px; color: #334155; line-height: 1.5; margin: 0;">
                    ${escapeHtml(trek.description || '')}
                </p>
            </div>

            <!-- Scenic Highlights -->
            ${highlightsHtml ? `
            <div style="margin-bottom: 18px;">
                <h3 style="font-size: 13px; font-weight: 800; text-transform: uppercase; color: #1e293b; letter-spacing: 0.5px; margin: 0 0 8px 0; border-left: 3px solid #10b981; padding-left: 8px;">
                    Key Trail Highlights
                </h3>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px;">
                    ${highlightsHtml}
                </div>
            </div>
            ` : ''}

            <!-- Day-Wise Expedition Itinerary Table -->
            <div style="margin-bottom: 20px; page-break-inside: avoid;">
                <h3 style="font-size: 13px; font-weight: 800; text-transform: uppercase; color: #1e293b; letter-spacing: 0.5px; margin: 0 0 8px 0; border-left: 3px solid #06b6d4; padding-left: 8px;">
                    Day-Wise Expedition Itinerary & Elevation Profile
                </h3>
                <table style="width: 100%; border-collapse: collapse; font-size: 11px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;">
                    <thead>
                        <tr style="background: #f1f5f9; color: #334155; font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 2px solid #cbd5e1;">
                            <th style="padding: 8px; text-align: left; width: 62px;">Day</th>
                            <th style="padding: 8px; text-align: left;">Trail Route & Description</th>
                            <th style="padding: 8px; text-align: left; width: 140px;">Night Camp & Altitude</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${itineraryRowsHtml}
                    </tbody>
                </table>
            </div>

            <!-- Permits & Documents Section (Two Column) -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 18px; page-break-inside: avoid;">
                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 14px;">
                    <h4 style="font-size: 12px; font-weight: 800; color: #1e293b; margin: 0 0 6px 0; display: flex; align-items: center; gap: 6px;">
                        📋 Required Government Permits
                    </h4>
                    <ul style="margin: 0 0 8px 0; padding-left: 16px;">
                        ${permitsHtml}
                    </ul>
                    <div style="font-size: 10px; color: #64748b;">
                        <strong>Fees:</strong> ${escapeHtml(permits.fee_details)}<br>
                        <strong>Checkpost:</strong> ${escapeHtml(permits.issuing_office)}
                    </div>
                </div>

                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 14px;">
                    <h4 style="font-size: 12px; font-weight: 800; color: #1e293b; margin: 0 0 6px 0; display: flex; align-items: center; gap: 6px;">
                        📄 Mandatory Identification & Medical Docs
                    </h4>
                    <ul style="margin: 0; padding-left: 16px;">
                        ${docsHtml}
                    </ul>
                </div>
            </div>

            <!-- High Altitude Gear & Safety Rules -->
            <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 12px 14px; margin-bottom: 18px; page-break-inside: avoid;">
                <h4 style="font-size: 12px; font-weight: 800; color: #166534; margin: 0 0 6px 0;">
                    🎒 3-Layer Packing & Altitude Sickness (AMS) Protocol
                </h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 10.5px; color: #14532d; line-height: 1.4;">
                    <div>
                        <strong>• Layering:</strong> Base (thermal) + Mid (fleece) + Outer (-10°C down jacket).<br>
                        <strong>• Footwear:</strong> Waterproof high-ankle shoes with deep lugs + 4-5 pairs socks.<br>
                        <strong>• Gear:</strong> 50-60L rucksack with rain cover, UV400 sunglasses, headlamp.
                    </div>
                    <div>
                        <strong>• Hydration:</strong> Drink 4-5 liters of water daily with ORS/electrolytes.<br>
                        <strong>• Golden Rule:</strong> <em>Climb High, Sleep Low</em>. Never ascend with headache or nausea.<br>
                        <strong>• Diamox:</strong> Consult doctor before taking preventive 125-250mg dose.
                    </div>
                </div>
            </div>

            <!-- Emergency SOS Helpline Directory -->
            <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 10px 14px; margin-bottom: 16px; page-break-inside: avoid;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong style="font-size: 11px; color: #991b1b; display: block;">🚨 Mountain Rescue & Emergency SOS Numbers</strong>
                        <span style="font-size: 10px; color: #7f1d1d;">National Disaster Management: <strong>112 / 1070</strong> | Medical Ambulance: <strong>108</strong> | SDRF Helpline: <strong>1070</strong></span>
                    </div>
                    <span style="font-size: 10px; font-weight: 700; color: #dc2626; background: #ffffff; padding: 3px 8px; border-radius: 4px; border: 1px solid #fca5a5;">24x7 Helpline</span>
                </div>
            </div>

            <!-- Document Footer -->
            <div style="border-top: 1px solid #e2e8f0; padding-top: 10px; display: flex; justify-content: space-between; align-items: center; font-size: 9.5px; color: #94a3b8;">
                <span>Generated by <strong>Trekkers Heaven</strong> (www.trekkersheaven.com) • Clean Mountain Trail Initiative</span>
                <span>Leave No Trace • Respect Nature • Mountain Safety First</span>
            </div>
        `;

        document.body.appendChild(printContainer);

        // Check if html2pdf is loaded
        if (typeof html2pdf === 'function') {
            const safeName = trek.name.replace(/[^a-zA-Z0-9]/g, '_');
            const opt = {
                margin:       [8, 8, 8, 8],
                filename:     `TrekkersHeaven_${safeName}_Expedition_Guide.pdf`,
                image:        { type: 'jpeg', quality: 0.98 },
                html2canvas:  { scale: 2, useCORS: true, logging: false },
                jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' },
                pagebreak:    { mode: ['avoid-all', 'css', 'legacy'] }
            };

            await html2pdf().set(opt).from(printContainer).save();
            printContainer.remove();
            showToast(`PDF Guide for ${trek.name} downloaded successfully! 🏔️`, 'success');
        } else {
            // Fallback: Use browser print engine
            printContainer.remove();
            const printWindow = window.open('', '_blank');
            if (printWindow) {
                printWindow.document.write(`
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>${escapeHtml(trek.name)} - Expedition Guide</title>
                        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
                        <style>
                            body { margin: 0; padding: 20px; font-family: 'Plus Jakarta Sans', sans-serif; }
                            @media print { body { padding: 0; } }
                        </style>
                    </head>
                    <body>
                        ${printContainer.innerHTML}
                    </body>
                    </html>
                `);
                printWindow.document.close();
                printWindow.focus();
                setTimeout(() => {
                    printWindow.print();
                }, 500);
            }
        }
    } catch (err) {
        console.error('Error generating PDF guide:', err);
        showToast('Could not generate PDF guide. Please try again.', 'danger');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalContent || '<i class="fa-solid fa-file-pdf"></i> Download PDF Guide';
        }
    }
}
