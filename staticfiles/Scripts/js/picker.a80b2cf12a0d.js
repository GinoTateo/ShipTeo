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
    let expectedCode = items[currentItemIndex].bayCode; // Assume each item has a 'bayCode' field

    if (scannedCode === expectedCode) {
        displayItemDetails(items[currentItemIndex]);
        currentItemIndex++; // Move to the next item
        if (currentItemIndex >= items.length) {
            completePicking(); // Call a function to handle completion
        }
    } else {
        alert("Incorrect bay. Please try again.");
    }
}

function displayItemDetails(item) {
    document.getElementById('bay-location').textContent = item.bay;
    document.getElementById('item-quantity').textContent = 'Quantity to pick: ' + item.quantity;
    // Update any other details necessary for picking
}

function completePicking() {
    alert("All items picked. Proceed to checkout or verification.");
    Quagga.stop(); // Stop the scanner when done
}

document.addEventListener('DOMContentLoaded', function() {
    setupScanner(); // Initialize the scanner when the document is ready
});
