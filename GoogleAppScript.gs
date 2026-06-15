function doGet(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var data = sheet.getDataRange().getValues();
    
    // NEW: Check if the bot wants a list of available resource names
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

    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var data = sheet.getDataRange().getValues();
    
    // Check if the bot sent a specific resource filter (e.g., !clanstatus cryotic)
    // We convert it to lowercase to make the search case-insensitive
    var resourceFilter = (e && e.parameter && e.parameter.resource) ? e.parameter.resource.toLowerCase().trim() : null;
    
    var overview = {};
    
    // Loop through rows starting from row 2 (Index 1)
    for (var i = 1; i < data.length; i++) {
      var player = data[i][1]; // Column B
      var item = data[i][2];   // Column C
      var amount = parseInt(data[i][3]); // Column D
      
      if (!player || !item || isNaN(amount)) continue;
      
      // If a filter is active, skip any item that doesn't match the filter
      if (resourceFilter && item.toLowerCase().trim() !== resourceFilter) {
        continue;
      }
      
      // Build the nested object: overview[player][item] = total_amount
      if (!overview[player]) {
        overview[player] = {};
      }
      if (!overview[player][item]) {
        overview[player][item] = 0;
      }
      
      overview[player][item] += amount;
    }
    
    return ContentService.createTextOutput(JSON.stringify({
      "status": "success",
      "filterActive": resourceFilter !== null,
      "filteredResource": resourceFilter,
      "data": overview
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