const SERVER_URL = "https://apple-game-w2wk.onrender.com";

let generatedCode = "";
let balance = 0.00;
let gameStarted = false;
let currentRow = 0;
let betAmount = 10;
let userNumericId = "";
let currentEmail = "";

const multipliers = [1.22, 1.44, 1.86, 3.51, 4.03, 5.51, 6.43, 11.00, 22.00, 63.00, 150.00];
const wormCounts = [1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4];
let rowStates = [];

// Авто-санҷиш ҳангоми кушодани сайт
window.onload = function() {
    let savedEmail = localStorage.getItem('apple_registered_email');
    let savedId = localStorage.getItem('apple_numeric_id');

    // Агар корбар аллакай сабти ном шуда бошад, бозиро фавран мекушоем
    if (savedEmail && savedId) {
        document.getElementById("landing-container").style.display = "none";
        document.getElementById("game-main-container").style.display = "flex";
        
        currentEmail = savedEmail;
        userNumericId = savedId;
        document.getElementById('userIdDisplay').innerText = `ID рақамӣ: ${userNumericId} (${currentEmail})`;
        
        initRows();
        syncBalanceFromServer();
        setInterval(syncBalanceFromServer, 2000);
    }
};

function goToGame() {
    let savedEmail = localStorage.getItem('apple_registered_email');
    let savedId = localStorage.getItem('apple_numeric_id');

    document.getElementById("landing-container").style.display = "none";

    // Агар сабти ном шуда бошад, бозиро мекушоем
    if (savedEmail && savedId) {
        document.getElementById("game-main-container").style.display = "flex";
        currentEmail = savedEmail;
        userNumericId = savedId;
        document.getElementById('userIdDisplay').innerText = `ID рақамӣ: ${userNumericId} (${currentEmail})`;
        initRows();
        syncBalanceFromServer();
        setInterval(syncBalanceFromServer, 2000);
    } else {
        // Агар сабти ном нашуда бошад, саҳифаи регистратсияро нишон медиҳем
        document.getElementById("auth-container").style.display = "flex";
    }
}

function sendVerificationCode() {
    const email = document.getElementById("userEmail").value.trim();
    if (!email) {
        alert("Лутфан почтаатонро ворид кунед!");
        return;
    }

    currentEmail = email;
    generatedCode = Math.floor(1000 + Math.random() * 9000).toString();

    const templateParams = {
        to_email: email,
        pass_code: generatedCode
    };

    emailjs.send("service_apple", "template_ws1eto8", templateParams)
        .then(function(response) {
            alert("Коди тасдиқ ба почтаи " + email + " фиристода шуд!");
            document.getElementById("step-email").style.display = "none";
            document.getElementById("step-verify").style.display = "flex";
        }, function(error) {
            console.error("Хатогӣ:", error);
            alert("Хатогӣ ҳангоми фиристодани почта рӯй дод.");
        });
}

function verifyUserCode() {
    const userCode = document.getElementById("enteredCode").value.trim();
    if (userCode === generatedCode) {
        alert("Бақайдгирӣ бо муваффақият гузашт! Хуш омадед!");
        
        userNumericId = Math.floor(10000000 + Math.random() * 90000000).toString();
        
        localStorage.setItem('apple_registered_email', currentEmail);
        localStorage.setItem('apple_numeric_id', userNumericId);

        document.getElementById("auth-container").style.display = "none";
        document.getElementById("game-main-container").style.display = "flex";
        document.getElementById('userIdDisplay').innerText = `ID рақамӣ: ${userNumericId} (${currentEmail})`;
        
        initRows();
        syncBalanceFromServer();
        setInterval(syncBalanceFromServer, 2000);
    } else {
        alert("Код нодуруст аст! Лутфан аз нав санҷед.");
    }
}

function openBot(actionType) {
    const url = `https://t.me/apple_game_tajik_bot?start=${actionType}_${userNumericId}`;
    window.open(url, '_blank');
}

function requestWithdraw() {
    if (gameStarted) {
        alert("Имкон надорад, бозӣ давом дорад!");
        return;
    }
    if (balance < 25) {
        alert("❌ Рад шуд! Миқдори маблағ бояд аз 25 сомонӣ зиёд бошад.");
        return;
    }
    
    const url = `https://t.me/apple_game_tajik_bot?start=withdraw_${userNumericId}_${balance.toFixed(2)}`;
    window.open(url, '_blank');
}

function initRows() {
    let container = document.getElementById('rowsContainer');
    container.innerHTML = '';
    rowStates = [];

    for (let i = 10; i >= 0; i--) {
        let rowDiv = document.createElement('div');
        rowDiv.className = 'row-level';
        rowDiv.id = `row-${i}`;

        let multSpan = document.createElement('div');
        multSpan.className = 'row-mult' + (multipliers[i] > 10 ? ' high' : '');
        multSpan.innerText = 'x' + multipliers[i].toFixed(2);
        rowDiv.appendChild(multSpan);

        let applesDiv = document.createElement('div');
        applesDiv.className = 'apples-container';

        let boxes = [];
        for (let j = 0; j < 5; j++) {
            let box = document.createElement('div');
            box.className = 'apple-box';
            box.innerText = '?';
            box.onclick = () => chooseApple(i, j);
            applesDiv.appendChild(box);
            boxes.push({ element: box, hasWorm: false });
        }
        rowDiv.appendChild(applesDiv);
        container.appendChild(rowDiv);
        rowStates[i] = { boxes: boxes, active: false };
    }
    setRowActive(0);
}

function setRowActive(rowIdx) {
    for (let i = 0; i <= 10; i++) {
        let rDiv = document.getElementById(`row-${i}`);
        if (i === rowIdx && gameStarted) {
            rDiv.style.borderColor = '#ffc107';
            rowStates[i].active = true;
        } else {
            rDiv.style.borderColor = '#2a3b5c';
            rowStates[i].active = false;
        }
    }
}

function setBet(val) { document.getElementById('betInput').value = val; }
function changeBet(delta) {
    let inp = document.getElementById('betInput');
    let v = parseInt(inp.value) || 0;
    inp.value = Math.max(1, v + delta);
}

async function updateServerBalance(amountChange) {
    if (!userNumericId) return;
    try {
        const res = await fetch(`${SERVER_URL}/update?game_id=${userNumericId}&amount=${amountChange}`);
        const data = await res.json();
        if (data && typeof data.balance !== 'undefined') {
            balance = Number(data.balance);
            document.getElementById('balance').innerText = balance.toFixed(2);
        }
    } catch (e) {
        console.error("Хатогӣ дар навсозии баланс:", e);
    }
}

async function handleGameAction() {
    if (!gameStarted) {
        betAmount = parseFloat(document.getElementById('betInput').value);
        await syncBalanceFromServer();
        
        if (betAmount > balance) { 
            alert("Недостаточно средств! Пополните через бота"); 
            openBot('topup');
            return; 
        }
        
        await updateServerBalance(-betAmount);
        
        gameStarted = true;
        currentRow = 0;
        
        rowStates.forEach((row, index) => {
            let wCount = wormCounts[index];
            let wormIndices = [];
            while(wormIndices.length < wCount) {
                let randIdx = Math.floor(Math.random() * 5);
                if(!wormIndices.includes(randIdx)) wormIndices.push(randIdx);
            }

            row.boxes.forEach((b, idx) => {
                b.hasWorm = wormIndices.includes(idx);
                b.element.innerText = '?';
                b.element.className = 'apple-box';
            });
        });

        setRowActive(currentRow);
        document.getElementById('actionBtn').innerText = "ЗАБРАТЬ ВЫИГРЫШ";
        document.getElementById('actionBtn').style.background = "linear-gradient(135deg, #22c55e, #15803d)";
        document.getElementById('actionBtn').style.color = "#fff";
    } else {
        let win = betAmount * (currentRow > 0 ? multipliers[currentRow - 1] : multipliers[0]);
        await updateServerBalance(win);
        
        revealAllApples();
        alert(`Вы успешно забрали выигрыш: +${win.toFixed(2)} смн`);
        gameStarted = false;
        document.getElementById('actionBtn').innerText = "СДЕЛАТЬ СТАВКУ";
        document.getElementById('actionBtn').style.background = "linear-gradient(135deg, #ffc107, #e0a800)";
        document.getElementById('actionBtn').style.color = "#0f141f";
    }
}

function chooseApple(rowIdx, boxIdx) {
    if (!gameStarted || !rowStates[rowIdx].active) return;

    let box = rowStates[rowIdx].boxes[boxIdx];
    if (box.hasWorm) {
        box.element.innerText = '💀';
        box.element.className = 'apple-box lose';
        revealAllApples();
        alert("Попался червивый себ! Вы проиграли ставку.");
        gameStarted = false;
        document.getElementById('actionBtn').innerText = "СДЕЛАТЬ СТАВКУ";
        document.getElementById('actionBtn').style.background = "linear-gradient(135deg, #ffc107, #e0a800)";
        document.getElementById('actionBtn').style.color = "#0f141f";
    } else {
        box.element.innerText = '🍏';
        box.element.className = 'apple-box win';
        
        if (rowIdx < 10) {
            currentRow = rowIdx + 1;
            setRowActive(currentRow);
        } else {
            let win = betAmount * multipliers[10];
            updateServerBalance(win);
            
            revealAllApples();
            alert(`Поздравляем! Вы достигли вершины (x150)! Выигрыш: +${win.toFixed(2)} смн`);
            gameStarted = false;
            document.getElementById('actionBtn').innerText = "СДЕЛАТЬ СТАВКУ";
            document.getElementById('actionBtn').style.background = "linear-gradient(135deg, #ffc107, #e0a800)";
            document.getElementById('actionBtn').style.color = "#0f141f";
        }
    }
}

function revealAllApples() {
    rowStates.forEach(row => {
        row.boxes.forEach(b => {
            if(b.hasWorm) {
                b.element.innerText = '💀';
                if(!b.element.classList.contains('lose')) b.element.classList.add('revealed');
            } else {
                b.element.innerText = '🍏';
                if(!b.element.classList.contains('win')) b.element.classList.add('revealed');
            }
        });
    });
}

async function syncBalanceFromServer() {
    if (!userNumericId) return;
    try {
        console.log("Талоши гирифтани баланс барои ID:", userNumericId); // Лог илова кардем
        const res = await fetch(`${SERVER_URL}/balance?game_id=${userNumericId}`);
        const data = await res.json();
        
        console.log("Ҷавоби сервер:", data); // Инро дар Консоль мебинед
        
        if (data && typeof data.balance !== 'undefined') {
            balance = Number(data.balance);
            const balanceEl = document.getElementById('balance');
            if (balanceEl) {
                balanceEl.innerText = balance.toFixed(2);
            }
        }
    } catch (e) {
        console.error("Хатогӣ дар гирифтани баланс:", e);
    }
}
