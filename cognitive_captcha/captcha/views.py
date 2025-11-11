from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.utils import timezone
from django.shortcuts import render, redirect
from .models import CaptchaAttempt, Animation
import json
import random
import os
from django.conf import settings
import requests
import ipaddress

def get_client_ip(request):
    """
    More reliable IP detection with proper proxy handling
    """
    ip_headers = [
        'HTTP_X_REAL_IP',           # Set by your reverse proxy
        'HTTP_X_FORWARDED_FOR',     # Standard proxy header
        'REMOTE_ADDR',              # Direct connection
    ]
    
    for header in ip_headers:
        ip = request.META.get(header)
        if ip:
            # Handle X-Forwarded-For comma-separated list
            if header == 'HTTP_X_FORWARDED_FOR':
                ips = [ip.strip() for ip in ip.split(',')]
                ip = ips[0]  # First IP is the original client
            break
    else:
        ip = 'unknown'
    
    # Basic IP validation
    try:
        ipaddress.ip_address(ip)
        return ip
    except ValueError:
        return 'invalid'

@ensure_csrf_cookie
def captcha_page(request):
    return render(request, 'captcha_page.html')

def protected_page(request):
    return render(request, 'protected_page.html')

def first_page(request):
    return render(request, 'first_page.html')

@csrf_protect
@require_http_methods(["GET"])
def get_captcha(request):
    identifier = get_client_ip(request)
    attempt, _ = CaptchaAttempt.get_or_create_for_identifier(identifier)
    
    if attempt.is_blocked and attempt.blocked_until > timezone.now():
        return JsonResponse({'status': 'blocked'}, status=403)
    
    difficulty = determine_difficulty(attempt.attempts)
    challenge = generate_challenge_with_ai(difficulty)

    if not challenge:
        return JsonResponse({'status': 'error', 'message': 'System temporarily unavailable'}, status=500)

    captcha_id = random.randint(1000, 9999)
    request.session['captcha'] = {
        'id': captcha_id,
        'correct_answer': challenge['correct_answer'],
        'expires_at': (timezone.now() + timezone.timedelta(minutes=5)).isoformat()
    }
    
    return JsonResponse({
        'id': captcha_id,
        'difficulty': difficulty,
        'time_limit': 60 if difficulty >= 2 else None,
        'question': challenge['question'],
        'options': challenge['options'],
        'correct_answer': challenge['correct_answer'],
        'video_url': challenge['video_url'],
        'ai_generated': challenge['ai_generated']
    })

def determine_difficulty(attempts):
    if attempts >= 3:
        return 3
    if attempts >= 2:
        return 2
    return 1

def generate_challenge_with_ai(difficulty):
    """MAIN FUNCTION: Uses AI for questions with emergency fallback"""
    
    try:
        animation = Animation.objects.filter(is_active=True).order_by('?').first()
        
        if not animation:
            return None
        
        # TRY AI FIRST (90% of the time - normal operation)
        ai_question = generate_ai_question(animation.description)
        
        if ai_question:
            return {
                'question': ai_question['question'],
                'options': ai_question['options'],
                'correct_answer': ai_question['correct'],
                'video_url': f'/animations/{os.path.basename(animation.video_file.name)}',
                'ai_generated': True
            }
        
        # AI FAILED (10% emergency fallback)
        print("AI API failed, using emergency fallback")
        emergency_question = generate_emergency_fallback(animation.description)
        
        return {
            'question': emergency_question['question'],
            'options': emergency_question['options'],
            'correct_answer': emergency_question['correct'],
            'video_url': f'/animations/{os.path.basename(animation.video_file.name)}',
            'ai_generated': False
        }
        
    except Exception as e:
        print(f"Error in challenge generation: {e}")
        return None

def generate_ai_question(description):
    """PRIMARY AI QUESTION GENERATOR"""
    prompt = f"""
    VIDEO DESCRIPTION: {description}
    
    Create ONE specific multiple-choice question about what happened in this video.
    The question must be answerable ONLY by watching the video.
    
    Requirements:
    - Question must be specific to this exact video description
    - 4 answer options
    - One clearly correct answer based on the description
    - Wrong options should be plausible but incorrect
    
    Return ONLY JSON format:
    {{
        "question": "Specific question about this video scene",
        "options": ["CorrectAnswer", "Wrong1", "Wrong2", "Wrong3"],
        "correct": "CorrectAnswer"
    }}
    """
    
    try:
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization': f'Bearer {settings.GROQ_API_KEY}'},
            json={
                'model': 'llama-3.1-8b-instant',  # ← FIXED MODEL
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.7,
                'max_tokens': 500
            },
            timeout=15
        )
        
        # DEBUGGING ADDED HERE
        print(f"🔧 API Status: {response.status_code}")
        if response.status_code != 200:
            print(f"❌ GROQ ERROR: {response.text}")
            return None
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            
            # Parse JSON response
            question_data = json.loads(ai_response)
            
            # Validate response
            if all(key in question_data for key in ['question', 'options', 'correct']):
                print("✅ AI question generated successfully!")
                return question_data
        else:
            print(f"❌ AI API error: {response.status_code}")
                
    except requests.exceptions.Timeout:
        print("❌ AI API timeout")
    except requests.exceptions.RequestException as e:
        print(f"❌ AI API connection error: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ AI response parsing error: {e}")
    except Exception as e:
        print(f"❌ AI unexpected error: {e}")
    
    return None

def generate_emergency_fallback(description):
    """EMERGENCY FALLBACK (10% cases only) - Uses OpenAI as backup"""
    print("🔄 Using OpenAI emergency fallback for:", description[:50] + "...")
    
    prompt = f"""
    VIDEO DESCRIPTION: {description}
    
    Create ONE specific multiple-choice question about what happened in this video.
    The question must be answerable ONLY by watching the video.
    
    Requirements:
    - Question must be specific to this exact video description
    - 4 answer options
    - One clearly correct answer based on the description
    - Wrong options should be plausible but incorrect
    - Return ONLY JSON format, no additional text
    
    Return ONLY JSON format:
    {{
        "question": "Specific question about this video scene",
        "options": ["CorrectAnswer", "Wrong1", "Wrong2", "Wrong3"],
        "correct": "CorrectAnswer"
    }}
    """
    
    try:
        print("🔧 Attempting OpenAI API call...")  
        # Try OpenAI API as backup
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={'Authorization': f'Bearer {settings.OPENAI_API_KEY}'},
            json={
                'model': 'gpt-3.5-turbo',  # or 'gpt-4' if available
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.7,
                'max_tokens': 500
            },
            timeout=10  # Shorter timeout for fallback
        )
        print(f"🔧 OpenAI API Status: {response.status_code}")  

        
        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            
            # Parse JSON response
            question_data = json.loads(ai_response)
            
            # Validate response
            if all(key in question_data for key in ['question', 'options', 'correct']):
                print("✅ OpenAI fallback question generated successfully!")
                return question_data
        else:
            print(f"❌ OpenAI fallback error: {response.status_code} - {response.text}")
            
            
    except requests.exceptions.Timeout:
        print("❌ OpenAI fallback timeout")
    except requests.exceptions.RequestException as e:
        print(f"❌ OpenAI fallback connection error: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ OpenAI fallback response parsing error: {e}")
    except Exception as e:
        print(f"❌ OpenAI fallback unexpected error: {e}")
    
    # Ultimate fallback - simple context-aware question
    return generate_ultimate_fallback(description)

def generate_ultimate_fallback(description):
    """ULTIMATE FALLBACK - Simple context-aware questions if all APIs fail"""
    description_lower = description.lower()
    
    # More context-aware fallbacks based on description keywords
    keywords_questions = {
        'ball': [
            {"question": "What happened to the ball in the video?", "options": ["It was caught", "It rolled away", "It disappeared", "It was thrown"], "correct": "It was caught"},
            {"question": "What was the main object in this scene?", "options": ["A ball", "A toy", "A fruit", "A book"], "correct": "A ball"}
        ],
        'dog': [
            {"question": "What did the dog do in this video?", "options": ["Ran and played", "Slept quietly", "Ate food", "Barked at something"], "correct": "Ran and played"},
            {"question": "Where was the animal in this scene?", "options": ["In a park", "Inside a house", "In water", "On a leash"], "correct": "In a park"}
        ],
        'child': [
            {"question": "What was the child doing in this video?", "options": ["Playing outside", "Reading a book", "Eating a snack", "Watching TV"], "correct": "Playing outside"},
            {"question": "Where was the child in this scene?", "options": ["Outside", "In a classroom", "At a table", "In bed"], "correct": "Outside"}
        ],
        'car': [
            {"question": "What happened with the vehicle in this video?", "options": ["It was parked", "It was moving", "It was being washed", "It was repaired"], "correct": "It was moving"},
            {"question": "What type of vehicle was in this scene?", "options": ["A car", "A bicycle", "A truck", "A motorcycle"], "correct": "A car"}
        ],
        'water': [
            {"question": "What happened near water in this video?", "options": ["Something was thrown in", "Someone swam", "It was calm", "It was raining"], "correct": "Something was thrown in"},
            {"question": "What body of water was in this scene?", "options": ["A pond", "A pool", "The ocean", "A puddle"], "correct": "A pond"}
        ]
    }
    
    # Find the most relevant keyword
    for keyword, questions in keywords_questions.items():
        if keyword in description_lower:
            return random.choice(questions)
    
    # Generic fallback if no keywords match
    generic_fallbacks = [
        {"question": "What was the main action in this video?", "options": ["An object moved", "People talked", "Someone waited", "Nothing happened"], "correct": "An object moved"},
        {"question": "What was the outcome of this scene?", "options": ["Something changed", "Everything stayed the same", "It started over", "It was interrupted"], "correct": "Something changed"},
        {"question": "What was the primary focus of this video?", "options": ["An object", "A person", "An animal", "A landscape"], "correct": "An object"}
    ]
    
    return random.choice(generic_fallbacks)

@csrf_protect
@require_http_methods(["POST"])
def submit_captcha_answer(request):
    try:
        data = json.loads(request.body)
        identifier = get_client_ip(request)
        attempt, _ = CaptchaAttempt.get_or_create_for_identifier(identifier)
        
        if attempt.is_blocked:
            return JsonResponse({'status': 'blocked'}, status=403)
        
        challenge = request.session.get('captcha')
        if not challenge or data.get('id') != challenge.get('id'):
            return JsonResponse({'status': 'invalid'}, status=400)

        if timezone.now() > timezone.datetime.fromisoformat(challenge['expires_at']):
            del request.session['captcha']
            return JsonResponse({'status': 'expired'}, status=400)
        
        is_correct = str(challenge['correct_answer']).lower() == str(data.get('answer')).lower()
        
        if is_correct:
            attempt.attempts = 0
            request.session['captcha_passed'] = True
            status = 'passed'
        else:
            attempt.attempts += 1
            if attempt.attempts >= 4:
                attempt.is_blocked = True
                attempt.blocked_until = timezone.now() + timezone.timedelta(hours=1)
            status = 'failed'
        
        attempt.save()
        
        if 'captcha' in request.session:
            del request.session['captcha']
        
        return JsonResponse({
            'status': status,
            'attempts': attempt.attempts,
            'difficulty': determine_difficulty(attempt.attempts),
            'ai_used': challenge.get('ai_generated', True)
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


