function doGet(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var data = sheet.getDataRange().getValues();
    
    // 1. Check for Action List request (Keep your existing feature untouched!)
    var action = (e && e.parameter && e.parameter.action) ? e.parameter.action.toLowerCase().trim() : null;
    if (action === "list") {
      var uniqueResources = [];
      for (var i = 1; i < data.length; i++) {
        var item = data[i][2]; // Column C
        if (item && uniqueResources.indexOf(item) === -1 && item !== "Nichts erkannt" && item !== "Unbekannt") {
          uniqueResources.push(item);
        }
      }
      return ContentService.createTextOutput(JSON.stringify({
        "status": "success",
        "resources": uniqueResources.sort()
      })).setMimeType(ContentService.MimeType.JSON);
    }

    // 2. Extract Query Parameters
    var resourceFilter = (e && e.parameter && e.parameter.resource) ? e.parameter.resource.toLowerCase().trim() : null;
    var playerFilter = (e && e.parameter && e.parameter.player) ? e.parameter.player.toLowerCase().trim() : null;
    var targetEngine = (e && e.parameter && e.parameter.target) ? e.parameter.target.toLowerCase().trim() : "player"; 
    
    var startDate = (e && e.parameter && e.parameter.start) ? new Date(e.parameter.start + "T00:00:00") : null;
    var endDate = (e && e.parameter && e.parameter.end) ? new Date(e.parameter.end + "T23:59:59") : null;

    var playerOverview = {}; 
    var globalOverview = {}; 

    // 3. Loop through logs starting from row 2 (Index 1)
    for (var i = 1; i < data.length; i++) {
      var timestamp = new Date(data[i][0]); // Column A
      var player = data[i][1];             // Column B
      var item = data[i][2];               // Column C
      var amount = parseInt(data[i][3]);   // Column D
      
      if (!player || !item || isNaN(amount)) continue;
      
      // Filter 1: Date Range check
      if (startDate && timestamp < startDate) continue;
      if (endDate && timestamp > endDate) continue;
      
      // Filter 2: Explicit Player check (Case-insensitive partial match)
      if (playerFilter && player.toLowerCase().trim().indexOf(playerFilter) === -1) continue;
      
      // Filter 3: Explicit Resource Asset check
      if (resourceFilter && item.toLowerCase().trim() !== resourceFilter) continue;
      
      // Accumulate Data
      if (targetEngine === "global") {
        if (!globalOverview[item]) globalOverview[item] = 0;
        globalOverview[item] += amount;
      } else {
        if (!playerOverview[player]) playerOverview[player] = {};
        if (!playerOverview[player][item]) playerOverview[player][item] = 0;
        playerOverview[player][item] += amount;
      }
    }
    
    // 4. Dispatch specific structural payload formatting back to Python
    return ContentService.createTextOutput(JSON.stringify({
      "status": "success",
      "target": targetEngine,
      "filterActive": resourceFilter !== null,
      "filteredResource": resourceFilter,
      "dateFilterActive": (startDate !== null || endDate !== null),
      "data": (targetEngine === "global") ? globalOverview : playerOverview
    })).setMimeType(ContentService.MimeType.JSON);
    
  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      "status": "error",
      "message": error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

function doPost(e) {
  try {
    var jsonString = e.postData.contents;
    var payload = JSON.parse(jsonString);
    
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var logSheet = ss.getSheetByName("Log") || ss.getSheets()[0]; // Fallback to first sheet
    var invSheet = ss.getSheetByName("Inventory");
    
    if (!invSheet) {
      return ContentService.createTextOutput(JSON.stringify({"status": "error", "message": "Inventory sheet tab not found!"})).setMimeType(ContentService.MimeType.JSON);
    }

    var action = payload.action || "log"; // 'log', 'sync', or 'consume'
    var donations = payload.donations;     // Array of {amount: X, item: "Y"}
    var username = payload.username || "System";
    
    var timestamp = new Date();

    // ==========================================
    // ACTION A: STANDARD DONATION LOGGING
    // ==========================================
    if (action === "log") {
      for (var i = 0; i < donations.length; i++) {
        // 1. Append row to continuous log stream
        logSheet.appendRow([timestamp, username, donations[i].item, donations[i].amount]);
        
        // 2. Adjust or Add to live Inventory balances
        adjustInventoryBalance(invSheet, donations[i].item, donations[i].amount);
      }
      return ContentService.createTextOutput(JSON.stringify({"status": "success", "message": "Donations logged and inventory increased successfully."})).setMimeType(ContentService.MimeType.JSON);
    }
    
    // ==========================================
    // ACTION B: ADMIN BASELINE INVENTORY SYNC
    // ==========================================
    if (action === "sync") {
      for (var i = 0; i < donations.length; i++) {
        setInventoryBalance(invSheet, donations[i].item, donations[i].amount);
      }
      return ContentService.createTextOutput(JSON.stringify({"status": "success", "message": "Inventory master baseline synced successfully."})).setMimeType(ContentService.MimeType.JSON);
    }

    // ==========================================
    // ACTION C: VAULT MATERIAL CONSUMPTION
    // ==========================================
    if (action === "consume") {
      for (var i = 0; i < donations.length; i++) {
        // Subtract by sending a negative value to our adjuster helper
        adjustInventoryBalance(invSheet, donations[i].item, -donations[i].amount);
      }
      return ContentService.createTextOutput(JSON.stringify({"status": "success", "message": "Inventory stock levels reduced successfully."})).setMimeType(ContentService.MimeType.JSON);
    }

  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({"status": "error", "message": error.toString()})).setMimeType(ContentService.MimeType.JSON);
  }
}

// --- HELPER SUB-METHODS FOR INVENTORY LOOKUPS ---

function adjustInventoryBalance(sheet, itemName, amountToChange) {
  var data = sheet.getDataRange().getValues();
  var foundRow = -1;
  
  for (var i = 1; i < data.length; i++) {
    if (data[i][0].toString().toLowerCase().trim() === itemName.toLowerCase().trim()) {
      foundRow = i + 1; // Convert back to standard 1-based Row Index
      break;
    }
  }
  
  if (foundRow !== -1) {
    var currentVal = parseInt(sheet.getRange(foundRow, 2).getValue()) || 0;
    var newVal = Math.max(0, currentVal + amountToChange); // Prevent negative stock levels
    sheet.getRange(foundRow, 2).setValue(newVal);
  } else if (amountToChange > 0) {
    // If it's a brand new item not in the spreadsheet yet, append it!
    sheet.appendRow([itemName, amountToChange]);
  }
}

function setInventoryBalance(sheet, itemName, absoluteAmount) {
  var data = sheet.getDataRange().getValues();
  var foundRow = -1;
  
  for (var i = 1; i < data.length; i++) {
    if (data[i][0].toString().toLowerCase().trim() === itemName.toLowerCase().trim()) {
      foundRow = i + 1;
      break;
    }
  }
  
  if (foundRow !== -1) {
    sheet.getRange(foundRow, 2).setValue(absoluteAmount);
  } else {
    sheet.appendRow([itemName, absoluteAmount]);
  }
}

function triggerRechte() {
  // Dieser Befehl zwingt Google, nach der externen Berechtigung zu fragen
  UrlFetchApp.fetch("https://www.google.com");
  Logger.log("Rechte erfolgreich erteilt!");

  // Ohne try-catch: Google MUSS jetzt nach den Rechten für Docs fragen
  var doc = DocumentApp.create("TestDokument");
  Logger.log("Dokument erstellt: " + doc.getUrl());
}