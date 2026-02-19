document.addEventListener('DOMContentLoaded', () => {
  console.log("AURA Stream has started.");

  //CONFIGURATION
  // const API_BASE_URL = 'http://localhost:3000/api';
  const API_BASE_URL = '/api';

  //VARIABLES
  const searchContainer = document.getElementById('search-container');
  const landingTitle = document.getElementById('landing-title');
  const riverViewContainer = document.getElementById('river-view-container');
  const wordViewOverlay = document.getElementById('word-view-overlay');

  const applyFiltersBtn = document.getElementById('apply-filters-btn');
  const backToRiverBtn = document.getElementById('back-to-river-btn');

  //Data Inputs
  const searchInput = document.getElementById('search-input');

  //Content Targets
  const row1 = document.getElementById('row-1');
  const row2 = document.getElementById('row-2');
  const row3 = document.getElementById('row-3');


  //STATE MANAGEMENT
  let isSearchActive = false;

  function activateSearchMode() {
    if (isSearchActive) return;
    isSearchActive = true;

    searchContainer.classList.remove('inset-0', 'justify-center', 'items-center');
    searchContainer.classList.add('top-0', 'pt-8');

    landingTitle.style.opacity = '0';
    setTimeout(() => landingTitle.style.display = 'none', 500);

    riverViewContainer.classList.remove('opacity-0');
  }

  // RENDER FUNCTIONS

  async function initializeRiver() {
    try {
      const response = await fetch(`${API_BASE_URL}/terms`);
      if (!response.ok) throw new Error('Network response was not ok');

      const riverData = await response.json();
      renderRiver(riverData);
    } catch (error) {
      console.error("Failed to fetch river data:", error);
    }
  }

  function renderRiver(terms) {
    //Clear rows so old results disappear
    row1.innerHTML = '';
    row2.innerHTML = '';
    row3.innerHTML = '';
    //If no terms ar found, stop here (screen stays empty)
    if (!terms || terms.length === 0) {
      console.log("No terms for this search.");
      return;
    }
    //Distribute terms into 3 buckets, which will then be processed separately to create an infinite loop. 
    let buckets = [[], [], []];

    //for testing: populate every row
    if (terms.length < 3) {
      buckets[0] = [...terms];
      buckets[1] = [...terms];
      buckets[2] = [...terms];
    } else {
      //with plenty of data--distribute normally
      terms.forEach((item, index) => {
        buckets[index % 3].push(item);
      });
    }

    const rowHTMLs = buckets.map(bucket => {
      let rowItems = [...bucket];
      if (rowItems.length === 0) return '';
      while (rowItems.length < 15) {
        rowItems = rowItems.concat(bucket);
      }
      //Create mirror copy 
      const seamlessList = [...rowItems, ...rowItems];
      return seamlessList.map(item => `
         <a href="#" class="river-chip group relative flex-shrink-0 flex items-center justify-center px-6 py-3 m-3 bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl text-white font-medium tracking-wide shadow-lg hover:bg-white/20 hover:scale-105 hover:shadow-davis-gold/50 transition-all duration-300"
    data-term-id="${item.id}">
      ${item.term}
    </a>`).join('');
    });

    row1.innerHTML = rowHTMLs[0];
    row2.innerHTML = rowHTMLs[1];
    row3.innerHTML = rowHTMLs[2];
  }

  function renderTermDetails(termObject) {
    document.getElementById('term-title').innerText = termObject.term;
    document.getElementById('term-definition').innerText = termObject.definition;
    document.getElementById('term-category').innerText = termObject.category.toUpperCase();

    //Render Sources
    const sourcesContainer = document.getElementById('sources-list');
    if (termObject.sources && termObject.sources.length > 0) {
      sourcesContainer.innerHTML = termObject.sources.map(source => `
        <div class="flex gap-4 p-4 rounded-xl bg-white border border-gray-100 hover:shadow-md transition-shadow">
          <img src="${source.img || 'https://placehold.co/100'}" class="w-16 h-16 rounded-lg object-cover bg-gray-200">
          <div>
            <h4 class="font-bold text-gray-900 leading-tight">${source.title}</h4>
            <p class="text-sm text-gray-500 mt-1">${source.summary || 'No summary available.'}</p>
          </div>
        </div>
      `).join('');
    } else {
      sourcesContainer.innerHTML = '<p class="text-gray-400 italic">No sources linked to this term.</p>';
    }

    // Render Related Topics (Ripples)
    const ripplesList = document.getElementById('related-ripples-list');
    if (termObject.ripples && termObject.ripples.length > 0) {
      ripplesList.innerHTML = termObject.ripples.map(r => `
        <li><a href="#" class="text-davis-dark hover:text-davis-gold underline underline-offset-4 decoration-wavy transition-colors" data-term-id="${r.id}">${r.term}</a></li>
      `).join('');
    } else {
      ripplesList.innerHTML = '<li class="text-gray-400">None</li>';
    }

    // Render Core Concepts (Rocks)
    const rocksContainer = document.getElementById('related-rocks-container');
    if (termObject.rocks && termObject.rocks.length > 0) {
      rocksContainer.innerHTML = termObject.rocks.map(rock => `
        <span class="bg-gray-100 text-gray-700 px-3 py-1 rounded-full text-xs font-semibold">${rock.name}</span>
      `).join('');
    } else {
      rocksContainer.innerHTML = '';
    }
  }

  // EVENT LISTENERS
  applyFiltersBtn.addEventListener('click', async (e) => {
    e.preventDefault();
    activateSearchMode();

    // Trigger visual transition
    const params = new URLSearchParams({
      search: searchInput.value,
      category: categoryFilter.value,
      date: dateFilter.value
    });

    try {
      const response = await fetch(`${API_BASE_URL}/terms?${params}`);
      const filteredResults = await response.json();
      renderRiver(filteredResults);
    } catch (error) {
      console.error("Filter Search Error:", error);
    }
  });

  //Opens Detail View when chip is clicked
  riverViewContainer.addEventListener('click', async (e) => {
    const chip = e.target.closest('.river-chip');
    if (chip) {
      e.preventDefault();
      const termId = chip.dataset.termId;

      try {
        const response = await fetch(`${API_BASE_URL}/terms/${termId}`);
        const termDetails = await response.json();

        renderTermDetails(termDetails);
        wordViewOverlay.classList.remove('hidden');
      } catch (error) {
        console.error("Detail Fetch Error:", error);
      }
    }
  });

  //Closes Detail view
  backToRiverBtn.addEventListener('click', () => {
    wordViewOverlay.classList.add('hidden');
  });

  // Kick off the initial load
  initializeRiver();
});
