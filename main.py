import os
import json
import base64
from datetime import datetime
from pathlib import Path
import anthropic
from fastapi import FastAPI, Request, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI(title="Mister Mac AI Copilot")

# Ensure data directory exists
Path("data").mkdir(exist_ok=True)

def load_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else []

# Load mock data
customers = load_json("data/customers.json", [])
sops = load_json("data/troubleshooting_sops.json", {})

# In-memory session storage (in production this would be a real database)
active_sessions = {}

@app.get("/", response_class=HTMLResponse)
async def home():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mister Mac AI Technician Copilot</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&family=Open+Sans:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&family=Open+Sans:ital,wght@0,400;0,600;1,400&display=swap');
        
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: 'Open Sans', sans-serif;
            background: #faf9f5;
            color: #4a4845;
            min-height: 100vh;
        }
        
        h1, h2, h3, h4, h5, button, label, .label, nav, .badge, th {
            font-family: 'Roboto', sans-serif;
        }
        
        .app-header {
            background: #ffffff;
            border-bottom: 1px solid #e8e6dc;
            padding: 0 24px;
            height: 56px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-family: 'Roboto', sans-serif;
            font-weight: 700;
            color: #141413;
        }
        
        .container {
            max-width: 1100px;
            margin: 0 auto;
            padding: 40px 24px;
        }
        
        .card {
            background: #ffffff;
            border: 1px solid #e8e6dc;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
        }
        
        .card-subtle {
            background: #f0efe9;
            border-radius: 12px;
            padding: 24px;
        }
        
        .btn-primary {
            background: #d97757;
            color: #ffffff;
            border: none;
            border-radius: 8px;
            padding: 12px 24px;
            font-family: 'Roboto', sans-serif;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
            transition: background 0.15s;
            margin-right: 12px;
        }
        .btn-primary:hover { background: #b85e3a; }
        .btn-primary:disabled { opacity: 0.45; cursor: not-allowed; }
        
        .btn-secondary {
            background: #f0efe9;
            color: #141413;
            border: 1px solid #e8e6dc;
            border-radius: 8px;
            padding: 12px 24px;
            font-family: 'Roboto', sans-serif;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
        }
        .btn-secondary:hover { background: #e8e6dc; }
        
        .btn-emergency {
            background: #c0463a;
            color: #ffffff;
            border: none;
            border-radius: 8px;
            padding: 12px 24px;
            font-family: 'Roboto', sans-serif;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
        }
        
        input, select, textarea {
            background: #ffffff;
            border: 1px solid #e8e6dc;
            border-radius: 8px;
            padding: 10px 14px;
            font-family: 'Open Sans', sans-serif;
            font-size: 14px;
            color: #141413;
            width: 100%;
            outline: none;
            margin-bottom: 16px;
        }
        input:focus, select:focus, textarea:focus {
            border-color: #d97757;
        }
        
        .field-label {
            display: block;
            font-family: 'Roboto', sans-serif;
            font-size: 11px;
            font-weight: 600;
            color: #b0aea5;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 7px;
        }
        
        .section-label {
            font-family: 'Roboto', sans-serif;
            font-size: 11px;
            font-weight: 600;
            color: #b0aea5;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 14px;
        }
        
        .badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 20px;
            font-family: 'Roboto', sans-serif;
            font-weight: 600;
            font-size: 12px;
        }
        .badge-green  { color: #788c5d; background: #e8eddf; }
        .badge-orange { color: #d97757; background: #f5e6df; }
        .badge-blue   { color: #6a9bcc; background: #e3eef7; }
        .badge-gray   { color: #b0aea5; background: #f0efe9; }
        
        .loading-state {
            text-align: center;
            color: #d97757;
            padding: 48px;
            font-family: 'Open Sans', sans-serif;
            font-size: 15px;
        }
        
        .empty-state {
            text-align: center;
            color: #b0aea5;
            padding: 48px;
            font-family: 'Open Sans', sans-serif;
            font-size: 14px;
        }
        
        .two-col {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }
        
        .three-col {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }
        
        .transcript-box {
            background: #f0efe9;
            border-radius: 8px;
            padding: 16px;
            margin: 16px 0;
            font-family: 'Open Sans', sans-serif;
            font-size: 14px;
            line-height: 1.6;
            max-height: 300px;
            overflow-y: auto;
        }
        
        .guidance-box {
            background: #e3eef7;
            border-radius: 8px;
            padding: 20px;
            margin: 16px 0;
        }
        
        .guidance-step {
            padding: 12px 0;
            border-bottom: 1px solid #e8e6dc;
        }
        .guidance-step:last-child {
            border-bottom: none;
        }
        
        .step-number {
            display: inline-block;
            width: 24px;
            height: 24px;
            background: #d97757;
            color: white;
            border-radius: 50%;
            text-align: center;
            line-height: 24px;
            font-size: 12px;
            font-weight: 600;
            margin-right: 12px;
        }
        
        .alert {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 14px;
            border-radius: 8px;
            font-family: 'Open Sans', sans-serif;
            font-size: 14px;
            margin-bottom: 16px;
        }
        .alert-info { background: #e3eef7; border: 1px solid #b8d4eb; color: #4a6a8a; }
        .alert-success { background: #e8eddf; border: 1px solid #b8ccaa; color: #4a6a3a; }
        
        .customer-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 20px;
        }
        
        .info-item {
            padding: 12px;
            background: #f0efe9;
            border-radius: 8px;
            text-align: center;
        }
        
        .info-label {
            font-size: 11px;
            font-weight: 600;
            color: #b0aea5;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 4px;
        }
        
        .info-value {
            font-size: 14px;
            color: #141413;
            font-weight: 500;
        }
        
        #statusIndicator {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            z-index: 1000;
        }
        
        .hidden { display: none; }
    </style>
</head>
<body>
    <header class="app-header">
        <div>🍎 Mister Mac AI Copilot</div>
        <div>
            <span class="badge badge-green">Demo Mode</span>
        </div>
    </header>
    
    <main class="container">
        <div id="statusIndicator" class="badge badge-gray hidden">Ready</div>
        
        <div class="alert alert-info">
            <div>ℹ️</div>
            <div>This demo simulates live call analysis. In production, this connects to your FaceTime/SharePlay sessions automatically.</div>
        </div>
        
        <!-- Start New Session -->
        <div class="card" id="sessionStart">
            <h2 style="color: #141413; margin-bottom: 16px;">Start Customer Support Session</h2>
            
            <form id="sessionForm">
                <label class="field-label">Select Customer</label>
                <select id="customerId" required>
                    <option value="">Choose a customer...</option>
                    <option value="cust_001">Sarah Johnson - iPhone 14 Pro</option>
                    <option value="cust_002">Mike Chen - iPhone 13 mini</option>
                    <option value="cust_003">Emily Davis - iPhone 15</option>
                </select>
                
                <label class="field-label">Upload Call Audio (simulates live capture)</label>
                <input type="file" id="audioFile" accept="audio/*" required>
                <div style="font-size: 12px; color: #b0aea5; margin-top: -12px; margin-bottom: 16px;">
                    Sample files available: email_issue.wav, scam_text.wav, app_problem.wav
                </div>
                
                <button type="submit" class="btn-primary">Start AI-Assisted Session</button>
            </form>
        </div>
        
        <!-- Active Session Interface -->
        <div id="activeSession" class="hidden">
            <div class="three-col">
                <div class="card">
                    <div class="section-label">Session Status</div>
                    <div class="badge badge-orange" id="sessionStatus">Listening...</div>
                </div>
                <div class="card">
                    <div class="section-label">Customer</div>
                    <div id="customerName" style="font-weight: 600; color: #141413;">-</div>
                </div>
                <div class="card">
                    <div class="section-label">Device</div>
                    <div id="customerDevice" style="font-weight: 600; color: #141413;">-</div>
                </div>
            </div>
            
            <div class="two-col">
                <div>
                    <!-- Customer Context -->
                    <div class="card">
                        <div class="section-label">Customer Context</div>
                        <div id="customerContext">
                            <div class="empty-state">Loading customer information...</div>
                        </div>
                    </div>
                    
                    <!-- Live Transcript -->
                    <div class="card">
                        <div class="section-label">Live Transcript</div>
                        <div id="transcript" class="transcript-box">
                            <div class="empty-state">Processing audio...</div>
                        </div>
                    </div>
                </div>
                
                <div>
                    <!-- AI Guidance -->
                    <div class="card">
                        <div class="section-label">AI Guidance for Technician</div>
                        <div id="guidance">
                            <div class="empty-state">AI will provide guidance once it understands the issue...</div>
                        </div>
                        
                        <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #e8e6dc;">
                            <button class="btn-emergency" onclick="escalateToScott()">🚨 Escalate to Scott</button>
                            <button class="btn-secondary" onclick="endSession()">End Session</button>
                        </div>
                    </div>
                    
                    <!-- Screen Share Simulation -->
                    <div class="card">
                        <div class="section-label">Customer Screen (via SharePlay)</div>
                        <div id="screenShare">
                            <div style="background: #f0efe9; border: 2px dashed #e8e6dc; border-radius: 8px; padding: 32px; text-align: center;">
                                <div style="margin-bottom: 12px;">📱</div>
                                <div style="color: #b0aea5;">Screen sharing will appear here</div>
                                <input type="file" id="screenUpload" accept="image/*" style="margin-top: 16px;">
                                <div style="font-size: 12px; color: #b0aea5; margin-top: 8px;">Upload screenshot to simulate</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </main>
    
    <script>
        let currentSessionId = null;
        let isProcessing = false;
        
        // Sample customer data
        const customers = {
            'cust_001': {
                name: 'Sarah Johnson',
                device: 'iPhone 14 Pro',
                lastIssue: 'Email sync problems',
                appointmentType: 'Technical Support',
                notes: 'Recurring customer, prefers step-by-step guidance'
            },
            'cust_002': {
                name: 'Mike Chen', 
                device: 'iPhone 13 mini',
                lastIssue: 'Suspicious text messages',
                appointmentType: 'Security Consultation',
                notes: 'First-time customer, needs education on scam detection'
            },
            'cust_003': {
                name: 'Emily Davis',
                device: 'iPhone 15',
                lastIssue: 'Missing apps after update',
                appointmentType: 'Technical Support',
                notes: 'Tech-savvy but frustrated with iOS changes'
            }
        };
        
        // Start session form handler
        document.getElementById('sessionForm').onsubmit = async function(e) {
            e.preventDefault();
            
            const customerId = document.getElementById('customerId').value;
            const audioFile = document.getElementById('audioFile').files[0];
            
            if (!customerId || !audioFile) {
                alert('Please select a customer and upload an audio file');
                return;
            }
            
            startSession(customerId, audioFile);
        };
        
        async function startSession(customerId, audioFile) {
            // Hide start form, show active session
            document.getElementById('sessionStart').classList.add('hidden');
            document.getElementById('activeSession').classList.remove('hidden');
            
            // Update status
            updateStatus('Processing...', 'orange');
            
            // Load customer info
            const customer = customers[customerId];
            document.getElementById('customerName').textContent = customer.name;
            document.getElementById('customerDevice').textContent = customer.device;
            
            // Show customer context
            document.getElementById('customerContext').innerHTML = `
                <div class="customer-info">
                    <div class="info-item">
                        <div class="info-label">Last Issue</div>
                        <div class="info-value">${customer.lastIssue}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Appointment Type</div>
                        <div class="info-value">${customer.appointmentType}</div>
                    </div>
                </div>
                <div class="alert alert-info">
                    <div>📝</div>
                    <div>${customer.notes}</div>
                </div>
            `;
            
            // Process the audio file
            await processAudio(audioFile);
        }
        
        async function processAudio(audioFile) {
            currentSessionId = 'session_' + Date.now();
            
            // Simulate transcript generation
            document.getElementById('transcript').innerHTML = '<div class="loading-state"><div style="font-size:32px; margin-bottom:12px;">⏳</div>Processing audio with AI...</div>';
            
            // Upload file and get transcript + guidance
            const formData = new FormData();
            formData.append('audio', audioFile);
            formData.append('sessionId', currentSessionId);
            
            try {
                const response = await fetch('/process-audio', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.error) {
                    throw new Error(result.error);
                }
                
                // Show transcript
                document.getElementById('transcript').innerHTML = `
                    <div style="margin-bottom: 16px;">
                        <strong style="color: #6a9bcc;">Customer:</strong> ${result.customerSpeech}
                    </div>
                    <div>
                        <strong style="color: #788c5d;">You:</strong> ${result.technicianSpeech || 'Hello, I can help you with that. Let me check what I can do...'}
                    </div>
                `;
                
                // Show AI guidance
                displayGuidance(result.guidance, result.issueType);
                
                updateStatus('Active', 'green');
                
            } catch (error) {
                console.error('Error processing audio:', error);
                document.getElementById('transcript').innerHTML = `
                    <div class="alert alert-warning">
                        <div>⚠️</div>
                        <div>Could not process audio. Using fallback scenario...</div>
                    </div>
                `;
                
                // Show fallback guidance
                displayFallbackGuidance();
            }
        }
        
        function displayGuidance(guidance, issueType) {
            const guidanceHtml = `
                <div class="guidance-box">
                    <div style="margin-bottom: 16px;">
                        <span class="badge badge-blue">${issueType}</span>
                    </div>
                    ${guidance.steps.map((step, index) => `
                        <div class="guidance-step">
                            <span class="step-number">${index + 1}</span>
                            <strong>${step.action}</strong>
                            <div style="margin-left: 36px; margin-top: 6px; color: #4a4845; font-size: 13px;">
                                ${step.details}
                            </div>
                        </div>
                    `).join('')}
                </div>
                
                ${guidance.next_if_stuck ? `
                    <div class="alert alert-info">
                        <div>💡</div>
                        <div><strong>If customer is still stuck:</strong> ${guidance.next_if_stuck}</div>
                    </div>
                ` : ''}
            `;
            
            document.getElementById('guidance').innerHTML = guidanceHtml;
        }
        
        function displayFallbackGuidance() {
            const fallbackGuidance = {
                steps: [
                    {
                        action: "Verify the customer's email account settings",
                        details: "Go to Settings > Mail > Accounts and check if the email account appears in the list"
                    },
                    {
                        action: "Check server settings",
                        details: "If Gmail: Incoming should be imap.gmail.com, Outgoing smtp.gmail.com. If Yahoo: imap.mail.yahoo.com"
                    },
                    {
                        action: "Test with app-specific password",
                        details: "If they have 2FA enabled, they need an app-specific password. Guide them to generate one in their email provider's settings"
                    }
                ],
                next_if_stuck: "Delete and re-add the email account completely. Sometimes iOS cache gets corrupted."
            };
            
            displayGuidance(fallbackGuidance, "Email Setup Issue");
        }
        
        function updateStatus(text, color) {
            const indicator = document.getElementById('statusIndicator');
            indicator.textContent = text;
            indicator.className = `badge badge-${color}`;
            indicator.classList.remove('hidden');
        }
        
        function escalateToScott() {
            if (confirm('This will escalate to Scott with full session context. Continue?')) {
                alert('🚨 Escalation sent to Scott!\n\nHe will receive:\n• Full transcript\n• Customer context\n• Steps attempted\n• Current issue status');
                
                updateStatus('Escalated to Scott', 'orange');
            }
        }
        
        function endSession() {
            if (confirm('End this support session?')) {
                document.getElementById('activeSession').classList.add('hidden');
                document.getElementById('sessionStart').classList.remove('hidden');
                document.getElementById('sessionForm').reset();
                updateStatus('Ready', 'gray');
                currentSessionId = null;
            }
        }
        
        // Screen sharing simulation
        document.getElementById('screenUpload').onchange = function(e) {
            const file = e.target.files[0];
            if (file && file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = function(event) {
                    document.getElementById('screenShare').innerHTML = `
                        <div>
                            <img src="${event.target.result}" style="max-width: 100%; border-radius: 8px; margin-bottom: 12px;">
                            <div class="alert alert-success">
                                <div>📱</div>
                                <div>Screen captured. AI can now provide visual guidance based on what the customer is showing.</div>
                            </div>
                        </div>
                    `;
                };
                reader.readAsDataURL(file);
            }
        };
    </script>
</body>
</html>"""

@app.post("/process-audio")
async def process_audio(audio: UploadFile = File(...), sessionId: str = Form(...)):
    try:
        # In a real implementation, this would:
        # 1. Use OpenAI Whisper to convert audio to text
        # 2. Parse the conversation
        # 3. Generate guidance using Claude
        
        # For demo, we'll simulate different scenarios based on filename
        filename = audio.filename.lower() if audio.filename else ""
        
        # Read the uploaded file (even though we're not processing it)
        audio_content = await audio.read()
        
        # Simulate different customer issues based on filename hints
        if "email" in filename:
            scenario = generate_email_scenario()
        elif "scam" in filename:
            scenario = generate_scam_scenario()
        elif "app" in filename:
            scenario = generate_app_scenario()
        else:
            # Default to email issue
            scenario = generate_email_scenario()
        
        # Use Claude to generate intelligent guidance
        guidance = await generate_ai_guidance(scenario["issue_description"], scenario["customer_speech"])
        
        return {
            "sessionId": sessionId,
            "customerSpeech": scenario["customer_speech"],
            "technicianSpeech": scenario.get("technician_speech"),
            "guidance": guidance,
            "issueType": scenario["issue_type"]
        }
        
    except Exception as e:
        print(f"Error processing audio: {e}")
        return {"error": "Failed to process audio. Please try again."}

async def generate_ai_guidance(issue_description, customer_speech):
    """Generate step-by-step guidance using Claude API"""
    try:
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        
        system_prompt = """You are an AI assistant helping junior technicians at Mister Mac (Apple technical support). 
        
        Your job is to provide clear, step-by-step guidance that a junior technician can follow to help customers with iPhone issues.
        
        Guidelines:
        - Provide 3-5 specific, actionable steps
        - Use simple language that both the tech and customer can understand
        - Include exactly what to say to the customer
        - Focus on the most common solutions first
        - If needed, suggest what to do if the customer is still stuck
        
        Format your response as JSON with this structure:
        {
            "steps": [
                {
                    "action": "Brief action title",
                    "details": "Exactly what to say and do"
                }
            ],
            "next_if_stuck": "What to try if steps don't work (optional)"
        }"""
        
        user_message = f"""Customer issue: {issue_description}
        
        Customer said: "{customer_speech}"
        
        Generate step-by-step guidance for the technician to resolve this issue."""
        
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )
        
        # Parse the JSON response
        guidance_text = response.content[0].text.strip()
        
        # Try to extract JSON from the response
        import re
        json_match = re.search(r'\{.*\}', guidance_text, re.DOTALL)
        if json_match:
            guidance_json = json.loads(json_match.group())
            return guidance_json
        else:
            # Fallback if JSON parsing fails
            return {
                "steps": [
                    {
                        "action": "Assess the situation",
                        "details": "Ask the customer to describe exactly what's happening and when it started"
                    },
                    {
                        "action": "Try the most common solution",
                        "details": guidance_text[:200] + "..."
                    }
                ]
            }
            
    except Exception as e:
        print(f"Error generating AI guidance: {e}")
        # Return fallback guidance
        return {
            "steps": [
                {
                    "action": "Gather more information",
                    "details": "Ask the customer when this issue started and what they were doing when it occurred"
                },
                {
                    "action": "Try basic troubleshooting",
                    "details": "Guide them to restart their iPhone by holding power button and volume down until they see the Apple logo"
                },
                {
                    "action": "Check settings",
                    "details": "Have them go to Settings and look for any red notification badges or error messages"
                }
            ],
            "next_if_stuck": "If these steps don't resolve it, escalate to Scott with all the details you've gathered"
        }

def generate_email_scenario():
    return {
        "issue_type": "Email Setup Issue",
        "customer_speech": "Hi, I'm having trouble with my email. After the iOS update yesterday, I'm not receiving any emails on my iPhone. I can see them fine on my computer, but nothing's coming through on the phone. It was working perfectly before the update.",
        "technician_speech": "I understand how frustrating that must be. Email sync issues after iOS updates are actually pretty common, and we should be able to get this fixed for you today.",
        "issue_description": "Customer's iPhone email stopped working after iOS update. Can receive emails on computer but not phone."
    }

def generate_scam_scenario():
    return {
        "issue_type": "Scam Text Detection",
        "customer_speech": "I got this text message saying it's from Apple and my account has been compromised. It's asking me to click a link and verify my information. It looks legitimate but I'm not sure if I should trust it. The message says I need to act within 24 hours or my account will be suspended.",
        "technician_speech": "You were absolutely right to be cautious about that message. Let me help you verify whether this is legitimate or a scam attempt.",
        "issue_description": "Customer received suspicious text claiming to be from Apple requesting account verification with urgent language and a link."
    }

def generate_app_scenario():
    return {
        "issue_type": "Missing Apps After Update", 
        "customer_speech": "I can't find half my apps after updating to iOS 17. Some of my most important apps just disappeared from my home screen. I've looked everywhere and I can't figure out where they went. Did the update delete them?",
        "technician_speech": "Don't worry, your apps are still there! iOS 17 changed how apps are organized, but we can easily find them and get them back where you want them.",
        "issue_description": "Customer cannot find apps after iOS update, likely moved to App Library or rearranged due to new iOS features."
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)