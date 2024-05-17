let currentItemIndex = 0;

document.addEventListener('DOMContentLoaded', function() {
    displayCurrentItem();
    document.getElementById('startScanner').addEventListener('click', function() {
        setupScanner();
    });
});

function displayCurrentItem() {
    if(currentItemIndex < items.length) {
        let currentItem = items[currentItemIndex];
        document.getElementById('bayName').textContent = currentItem.Location; // Make sure the key is 'Location'
        document.getElementById('scanResult').textContent = "Please scan the bay location: " + currentItem.Location;
    } else {
        document.getElementById('scanResult').textContent = "All items have been picked.";
    }
}

document.addEventListener('DOMContentLoaded', function() {
    displayCurrentItem();
});


function setupScanner() {
    Quagga.init({
        inputStream: {
            name: "Live",
            type: "LiveStream",
            target: document.querySelector('#scanner-container'),
        },
        decoder: {
            readers: ["code_128_reader"]
        }
    }, function(err) {
        if(err) {
            console.error(err);
            return;
        }
        Quagga.start();
    });

    Quagga.onDetected(function(data) {
        let scannedCode = data.codeResult.code;
        let expectedCode = items[currentItemIndex].bay; // Assuming each item has a 'bay' property

        if (scannedCode === expectedCode) {
            alert('Correct bay. Please pick ' + items[currentItemIndex].quantity + ' items.');
            currentItemIndex++;
            displayCurrentItem();
        } else {
            alert('Incorrect bay. Please try again.');
        }
    });
}
