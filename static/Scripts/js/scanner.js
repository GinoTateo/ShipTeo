document.addEventListener('DOMContentLoaded', function() {
    displayCurrentItem();
    document.getElementById('startScanner').addEventListener('click', function() {
        setupScanner();
    });
});

function displayCurrentItem() {
    if (currentItemIndex < items.length) {
        let currentItem = items[currentItemIndex];
        document.getElementById('bayName').textContent = currentItem.Location;
        document.getElementById('scanResult').textContent = "Please scan the bay location: " + currentItem.Location;
    } else {
        document.getElementById('scanResult').textContent = "All items have been picked.";
        Quagga.stop();  // Stop the scanner when all items have been picked
    }
}

function setupScanner() {
Quagga.init({
    inputStream: {
        name: "Live",
        type: "LiveStream",
        target: document.querySelector('#scanner-container'),
        constraints: {
            facingMode: "environment"
        }
    },
    decoder: {
        readers: ["code_128_reader"]
    }
}, function(err) {
    if (err) {
        console.error('Initialization error in Quagga:', err);
        alert('Failed to initialize the scanner: ' + err);
        return;
    }
    console.log('Initialization succeeded');
    Quagga.start();
});


    Quagga.onDetected(function(data) {
        let scannedCode = data.codeResult.code;
        let expectedCode = items[currentItemIndex].ItemNumber;  // Make sure the key matches expected barcode
        if (scannedCode === expectedCode.toString()) {
            alert('Correct bay. Please pick ' + items[currentItemIndex].Quantity + ' of ' + items[currentItemIndex].Description);
            Quagga.stop();  // Stop the scanner upon successful scan
            currentItemIndex++;
            displayCurrentItem();
        } else {
            alert('Incorrect bay. Please try again.');
        }
    });
}
