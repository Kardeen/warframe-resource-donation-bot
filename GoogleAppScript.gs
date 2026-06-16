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
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var payload = JSON.parse(e.postData.contents);
    
    var username = payload.username || "Unknown Player";
    var donations = payload.donations || []; // This is the verified array from Python
    
    if (donations.length === 0) {
      return ContentService.createTextOutput(JSON.stringify({
        "status": "error",
        "message": "No donations provided in payload structure"
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    var timestamp = new Date();
    
    // Loop through the clean data and log each item as a row
    for (var i = 0; i < donations.length; i++) {
      var entry = donations[i];
      sheet.appendRow([
        timestamp,
        username,
        entry.item,   // Already whitelisted clean name
        entry.amount  // Already validated integer amount
      ]);
    }
    
    return ContentService.createTextOutput(JSON.stringify({
      "status": "success",
      "message": donations.length + " rows added successfully."
    })).setMimeType(ContentService.MimeType.JSON);
    
  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      "status": "error",
      "message": error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
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