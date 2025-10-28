// DAILY JOB SEARCH AUTOMATION - Runs at 8am CET
// This script searches for jobs and adds them to your Google Sheet

// ============================================
// CONFIGURATION
// ============================================
const CONFIG = {
  YOUR_EMAIL: 'your-email@gmail.com', // CHANGE THIS
  SEARCH_QUERIES: [
    'digital product designer HealthTech Germany remote',
    'lead product designer MedTech Germany',
    'senior UX designer FinTech Berlin Hamburg',
    'product designer SaaS startup Germany remote',
    'founding designer HealthTech startup Germany'
  ],
  INDUSTRIES_PRIORITY: {
    'HealthTech': 'High',
    'MedTech': 'High',
    'FinTech': 'High',
    'SaaS': 'Medium',
    'Startup': 'Medium'
  },
  MAX_NEW_COMPANIES_PER_DAY: 5
};

// ============================================
// MAIN FUNCTION - Runs Daily at 8am
// ============================================
function dailyJobSearch() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Opportunities');
  const existingCompanies = getExistingCompanies(sheet);
  
  Logger.log('Starting daily job search...');
  Logger.log(`Currently tracking ${existingCompanies.size} companies`);
  
  const newCompanies = [];
  const today = Utilities.formatDate(new Date(), 'Europe/Berlin', 'yyyy-MM-dd');
  
  // Search for new opportunities
  for (const query of CONFIG.SEARCH_QUERIES) {
    Logger.log(`Searching: ${query}`);
    
    // Note: Apps Script can't directly web search, so this is a placeholder
    // In real implementation, you'd use a job API or web scraping service
    // For now, this demonstrates the structure
    
    const mockResults = searchJobs(query); // This would be your actual search
    
    for (const result of mockResults) {
      if (!existingCompanies.has(result.company) && newCompanies.length < CONFIG.MAX_NEW_COMPANIES_PER_DAY) {
        newCompanies.push([
          determinePriority(result),
          result.company,
          result.industry,
          result.type,
          result.location,
          result.jobLink,
          result.website,
          result.contact,
          'New Lead',
          today,
          '',
          result.notes
        ]);
      }
    }
  }
  
  // Add new companies to sheet
  if (newCompanies.length > 0) {
    const lastRow = sheet.getLastRow();
    sheet.getRange(lastRow + 1, 1, newCompanies.length, 12).setValues(newCompanies);
    Logger.log(`Added ${newCompanies.length} new companies`);
  } else {
    Logger.log('No new companies found today');
  }
  
  // Generate and send morning briefing
  sendMorningBriefing(sheet, newCompanies);
}

// ============================================
// HELPER FUNCTIONS
// ============================================

function getExistingCompanies(sheet) {
  const data = sheet.getDataRange().getValues();
  const companies = new Set();
  
  // Skip header row
  for (let i = 1; i < data.length; i++) {
    companies.add(data[i][1]); // Column B = Company Name
  }
  
  return companies;
}

function determinePriority(result) {
  for (const [industry, priority] of Object.entries(CONFIG.INDUSTRIES_PRIORITY)) {
    if (result.industry.includes(industry)) {
      return priority;
    }
  }
  return 'Medium';
}

function searchJobs(query) {
  // PLACEHOLDER: In production, integrate with:
  // - Job board APIs (Indeed, LinkedIn, etc.)
  // - Custom web scraping via UrlFetchApp
  // - RSS feeds from company career pages
  
  // For now, returning empty array
  // You'll integrate actual search in Phase 3
  return [];
}

function sendMorningBriefing(sheet, newCompanies) {
  const data = sheet.getDataRange().getValues();
  const today = Utilities.formatDate(new Date(), 'Europe/Berlin', 'yyyy-MM-dd');
  
  // Count companies by status
  const statusCounts = {};
  const needsAction = [];
  
  for (let i = 1; i < data.length; i++) {
    const status = data[i][8]; // Column I = Status
    const lastAction = data[i][10]; // Column K = Last Action
    const company = data[i][1]; // Column B = Company Name
    
    statusCounts[status] = (statusCounts[status] || 0) + 1;
    
    // Check if needs follow-up (no action in 5+ days)
    if (lastAction) {
      const daysSinceAction = Math.floor((new Date() - new Date(lastAction)) / (1000 * 60 * 60 * 24));
      if (daysSinceAction >= 5 && status === 'Applied') {
        needsAction.push(`${company} (applied ${daysSinceAction} days ago)`);
      }
    }
  }
  
  // Generate email content
  let emailBody = `
  <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <h2 style="color: #2c3e50;">🌅 Your Daily Job Search Briefing</h2>
      <p><strong>${today}</strong></p>
      
      <div style="background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0;">
        <h3 style="margin-top: 0;">📊 Pipeline Overview</h3>
        <ul style="list-style: none; padding: 0;">
  `;
  
  for (const [status, count] of Object.entries(statusCounts)) {
    emailBody += `<li><strong>${status}:</strong> ${count}</li>`;
  }
  
  emailBody += `
        </ul>
      </div>
  `;
  
  // New companies today
  if (newCompanies.length > 0) {
    emailBody += `
      <div style="background: #d5f4e6; padding: 15px; border-radius: 5px; margin: 20px 0;">
        <h3 style="margin-top: 0; color: #27ae60;">✨ ${newCompanies.length} New Companies Added</h3>
        <ul>
    `;
    
    for (const company of newCompanies) {
      emailBody += `<li><strong>${company[1]}</strong> - ${company[2]} (${company[0]} priority)</li>`;
    }
    
    emailBody += `
        </ul>
      </div>
    `;
  }
  
  // Action items
  if (needsAction.length > 0) {
    emailBody += `
      <div style="background: #ffe5e5; padding: 15px; border-radius: 5px; margin: 20px 0;">
        <h3 style="margin-top: 0; color: #c0392b;">⚡ Needs Follow-Up</h3>
        <ul>
    `;
    
    for (const item of needsAction) {
      emailBody += `<li>${item}</li>`;
    }
    
    emailBody += `
        </ul>
      </div>
    `;
  }
  
  // Today's recommendation
  emailBody += `
      <div style="background: #fff9e6; padding: 15px; border-radius: 5px; margin: 20px 0;">
        <h3 style="margin-top: 0; color: #f39c12;">🎯 Today's Focus</h3>
        <p><strong>Recommended actions for today:</strong></p>
        <ul>
  `;
  
  if (needsAction.length > 0) {
    emailBody += `<li>Follow up on ${needsAction.length} application(s)</li>`;
  }
  if (newCompanies.length > 0) {
    emailBody += `<li>Research the ${newCompanies.length} new companies added</li>`;
  }
  emailBody += `
          <li>Send 2-3 network outreach messages</li>
          <li>Apply to 2 new positions</li>
        </ul>
      </div>
      
      <p style="color: #7f8c8d; font-size: 14px; margin-top: 30px;">
        <a href="${SpreadsheetApp.getActiveSpreadsheet().getUrl()}" style="color: #3498db;">
          Open your tracker →
        </a>
      </p>
    </body>
  </html>
  `;
  
  // Send email
  MailApp.sendEmail({
    to: CONFIG.YOUR_EMAIL,
    subject: `📋 Daily Briefing: ${newCompanies.length} new leads, ${needsAction.length} need follow-up`,
    htmlBody: emailBody
  });
  
  Logger.log('Morning briefing sent');
}

// ============================================
// MANUAL TRIGGER FUNCTIONS (for testing)
// ============================================

function testDailySearch() {
  dailyJobSearch();
}

function setupDailyTrigger() {
  // Delete existing triggers
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => ScriptApp.deleteTrigger(trigger));
  
  // Create new trigger for 8am CET
  ScriptApp.newTrigger('dailyJobSearch')
    .timeBased()
    .atHour(8)
    .inTimezone('Europe/Berlin')
    .everyDays(1)
    .create();
    
  Logger.log('Daily trigger set up for 8am CET');
}
