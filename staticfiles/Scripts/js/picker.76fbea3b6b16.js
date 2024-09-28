let currentItemIndex = 0;

function setupScanner() {
    Quagga.init({
        inputStream: {
            name: "Live",
            type: "LiveStream",
            target: document.querySelector('#scanner-container') // Setup the target for QuaggaJS
        },
        decoder: {
            readers: ["code_128_reader"] // Adjust according to your barcode format
        }
    }, function(err) {
        if (err) {
            console.log(err);
            return;
        }
        console.log("Quagga initialized.");
        Quagga.start();
    });

    Quagga.onDetected(handleBarcodeDetected);
}

function handleBarcodeDetected(data) {
    let scannedCode = data.codeResult.code;
    let currentItem = orderItemsData[currentItemIndex];  // Use the global items array

    if (scannedCode === currentItem.Location) {  // Use 'Location' to compare
        displayItemDetails(currentItem);
        currentItemIndex++;
        if (currentItemIndex >= orderItemsData.length) {
            completePicking();
        }
    } else {
        alert("Incorrect bay. Please try again.");
    }
}


function displayItemDetails(item) {
    document.getElementById('bayName').textContent = 'Bay Location: ' + item.Location;
    document.getElementById('scanResult').textContent = 'Please pick quantity: ' + item.Quantity;
    // Any other item details you want to display can be added here
}



function completePicking() {
    alert("All items picked. Proceed to checkout or verification.");
    Quagga.stop(); // Stop the scanner when done
}

document.addEventListener('DOMContentLoaded', function() {
    setupScanner(); // Initialize the scanner when the document is ready
});
