document.addEventListener('DOMContentLoaded', () => {
    // --- Element Selectors ---
    const subjectInput = document.getElementById('ticket-subject');
    const descriptionInput = document.getElementById('ticket-description');
    const emailInput = document.getElementById('ticket-email');
    const getSuggestionBtn = document.getElementById('get-suggestion-btn');
    const raiseTicketBtn = document.getElementById('raise-ticket-btn');

    const suggestionContainer = document.getElementById('suggestion-container');
    const suggestionLoader = document.getElementById('suggestion-loader');
    const suggestionBox = document.getElementById('suggestion-box');

    const triageContainer = document.getElementById('triage-container');
    const triageLoader = document.getElementById('triage-loader');
    const triageBox = document.getElementById('triage-box');

    // --- Event Listeners ---
    getSuggestionBtn.addEventListener('click', handleGetSuggestion);
    raiseTicketBtn.addEventListener('click', handleRaiseTicket);

    // --- Handler Functions ---
    async function handleGetSuggestion() {
        const subject = subjectInput.value.trim();
        const description = descriptionInput.value.trim();

        if (!subject || !description) {
            alert('Please provide both a subject and a description.');
            return;
        }

        // --- FIX: Disable button to prevent multiple clicks ---
        getSuggestionBtn.disabled = true;
        getSuggestionBtn.textContent = 'Getting Suggestion...';

        // Reset UI for a new interaction
        raiseTicketBtn.disabled = false;
        raiseTicketBtn.textContent = 'This Didn\'t Help, Raise A Support Ticket';
        
        suggestionContainer.style.display = 'block';
        suggestionLoader.style.display = 'block';
        suggestionBox.innerHTML = ''; // Clear previous suggestion
        raiseTicketBtn.style.display = 'none';
        triageContainer.style.display = 'none';

        try {
            const response = await fetch('/get_suggestion', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ subject, description }),
            });

            if (!response.ok) throw new Error('Network response was not ok.');

            const data = await response.json();
            suggestionBox.innerHTML = `<p>${data.answer.replace(/\n/g, '<br>')}</p>`;

            if (data.route !== 'generic') {
                raiseTicketBtn.style.display = 'block';
            }

        } catch (error) {
            console.error('Fetch error:', error);
            suggestionBox.innerHTML = `<p class="error">Could not get a suggestion. Please try again.</p>`;
            raiseTicketBtn.style.display = 'block';
        } finally {
            suggestionLoader.style.display = 'none';
            // --- FIX: Re-enable button after process is complete ---
            getSuggestionBtn.disabled = false;
            getSuggestionBtn.textContent = 'Get Instant Suggestion';
        }
    }

    async function handleRaiseTicket() {
        const subject = subjectInput.value.trim();
        const description = descriptionInput.value.trim();
        const email = emailInput.value.trim();

        if (!subject || !description || !email) {
            alert('Subject, Email, and Description are all required to raise a ticket.');
            return;
        }

        // Hide the entire suggestion card immediately
        suggestionContainer.style.display = 'none';
        
        // Show the triage container and its loader
        triageContainer.style.display = 'block';
        triageLoader.style.display = 'block';
        triageBox.innerHTML = '';

        try {
            const response = await fetch('/create_ticket', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ subject, description, email }),
            });

            if (!response.ok) throw new Error('Network response was not ok.');
            const data = await response.json();
            
            triageBox.innerHTML = `
                <h2 class="card-header success-header">
                    Ticket Raised Successfully!
                </h2>
                <div class="card-content">
                    <div class="triage-item">
                        <span class="triage-label">Your Ticket ID:</span>
                        <span class="triage-value">${data.ticket_id}</span>
                    </div>
                    <p class="triage-footer">Thank you! Your ticket has been successfully logged. A member of our support team will be in touch via email shortly.</p>
                </div>
            `;

        } catch (error) {
            console.error('Fetch error:', error);
            triageBox.innerHTML = `<p class="error">Could not raise the ticket. Please try again.</p>`;
        } finally {
            triageLoader.style.display = 'none';
            // --- FIX: Re-enable main button so user can start a new ticket ---
            getSuggestionBtn.disabled = false;
            getSuggestionBtn.textContent = 'Get Instant Suggestion';
        }
    }
});
