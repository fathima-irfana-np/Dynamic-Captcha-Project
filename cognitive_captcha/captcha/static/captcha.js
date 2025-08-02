class CaptchaSystem {
    constructor() {
        this.elements = {
            canvas: document.getElementById('storyCanvas'),
            questionPanel: document.getElementById('questionPanel'),
            questionText: document.getElementById('questionText'),
            optionsDiv: document.getElementById('options'),
            resultMessage: document.getElementById('resultMessage'),
            difficultyIndicator: document.getElementById('difficulty-level'),
            timerContainer: document.getElementById('timer-container'),
            timerDisplay: document.getElementById('timer'),
            attemptsCounter: document.getElementById('attempts-count')
        };

        this.state = {
            difficulty: 1,
            failedAttempts: 0,
            timer: null
        };

        this.init();
    }

    init() {
        this.loadCaptcha();
        this.setupEventListeners();
    }

    setupEventListeners() {
        document.addEventListener('click', () => {
            if (this.state.failedAttempts > 0) {
                this.updateUI();
            }
        }, { once: true });
    }

    async loadCaptcha() {
        try {
            const response = await fetch('/get/', {
                headers: { 'X-Difficulty': this.state.difficulty }
            });

            if (response.status === 403) {
                this.showBlockedMessage();
                return;
            }

            const data = await response.json();
            this.state.currentChallenge = data;
            this.runAnimation(data.animation_data, () => this.showQuestion(data));
        } catch (error) {
            console.error('CAPTCHA error:', error);
            this.showResult('System error. Please refresh.', false);
        }
    }

    runAnimation(animationData, callback) {
        const { canvas } = this.elements;
        const ctx = canvas.getContext('2d');
        const actors = animationData.actors.map(a => ({
            ...a,
            x: -50,
            y: 100 + Math.random() * 100,
            active: false
        }));

        let animationId;
        const startTime = Date.now();

        const animate = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#f5f5f5';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            let allDone = true;
            const currentTime = Date.now() - startTime;

            actors.forEach(actor => {
                if (currentTime >= actor.delay * 1000) {
                    actor.active = true;
                    if (actor.x < canvas.width - 50) {
                        actor.x += this.state.difficulty >= 2 ? 3 : 2;
                        allDone = false;
                    }
                    this.drawActor(ctx, actor);
                } else {
                    allDone = false;
                }
            });

            if (allDone) {
                cancelAnimationFrame(animationId);
                setTimeout(callback, 1000);
            } else {
                animationId = requestAnimationFrame(animate);
            }
        };

        animate();
    }

    drawActor(ctx, actor) {
        ctx.fillStyle = actor.color;
        ctx.beginPath();
        ctx.arc(actor.x, actor.y, 15, 0, Math.PI * 2);
        ctx.fill();

        if (actor.object) {
            const [_, color] = actor.object.split('_');
            ctx.fillStyle = color;
            ctx.fillRect(actor.x - 10, actor.y - 30, 20, 20);
        }
    }

    showQuestion(data) {
        const { questionText, optionsDiv } = this.elements;
        questionText.textContent = data.question;
        optionsDiv.innerHTML = '';

        // Shuffle options but keep correct answer
        const options = [...new Set([...data.options, data.correct_answer])]
            .sort(() => Math.random() - 0.5);

        options.forEach(option => {
            const button = document.createElement('button');
            button.className = 'captcha-btn';
            button.textContent = option;
            button.onclick = () => this.verifyAnswer(option === data.correct_answer, data.id);
            optionsDiv.appendChild(button);
        });

        this.elements.questionPanel.style.display = 'block';
    }

    async verifyAnswer(isCorrect, challengeId) {
        if (isCorrect) {
            this.showResult("Success! Redirecting...", true);
            this.state.failedAttempts = 0;

            await fetch('/submit/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: challengeId, answer: 'passed' })
            });

            setTimeout(() => window.location.href = "/protected/", 1500);
        } else {
            this.state.failedAttempts++;
            this.showResult("Incorrect. Try again.", false);

            if (this.state.failedAttempts >= 10) {
                this.showBlockedMessage();
            } else {
                this.state.difficulty = Math.min(3, Math.floor(this.state.failedAttempts / 3) + 1);
                setTimeout(() => this.loadCaptcha(), 1500);
            }
        }

        this.updateUI();
    }

    updateUI() {
        const { difficultyIndicator, attemptsCounter, timerContainer } = this.elements;
        difficultyIndicator.textContent = this.state.difficulty;
        attemptsCounter.textContent = this.state.failedAttempts;

        if (this.state.difficulty >= 2) {
            timerContainer.style.display = 'block';
            this.startTimer(this.state.difficulty === 2 ? 60 : 45);
        } else {
            timerContainer.style.display = 'none';
            clearInterval(this.state.timer);
        }
    }

    startTimer(seconds) {
        clearInterval(this.state.timer);
        let timeLeft = seconds;
        this.updateTimer(timeLeft);

        this.state.timer = setInterval(() => {
            timeLeft--;
            this.updateTimer(timeLeft);

            if (timeLeft <= 0) {
                clearInterval(this.state.timer);
                this.handleTimeout();
            }
        }, 1000);
    }

    updateTimer(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        this.elements.timerDisplay.textContent = `${mins}:${secs < 10 ? '0' : ''}${secs}`;
    }

    handleTimeout() {
        this.state.failedAttempts++;
        this.showResult("Time expired!", false);
        this.updateUI();
        setTimeout(() => this.loadCaptcha(), 1500);
    }

    showResult(message, isSuccess) {
        const { resultMessage } = this.elements;
        resultMessage.textContent = message;
        resultMessage.className = `captcha-result ${isSuccess ? 'success' : 'error'}`;
        resultMessage.style.display = 'block';
    }

    showBlockedMessage() {
        this.elements.questionPanel.innerHTML = `
            <div class="blocked-message">
                <h3>Access Blocked</h3>
                <p>Too many failed attempts. Please try again later.</p>
            </div>
        `;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => new CaptchaSystem());