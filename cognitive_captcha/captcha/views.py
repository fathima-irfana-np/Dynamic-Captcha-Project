from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.utils import timezone
from django.shortcuts import render, redirect
from .models import CaptchaAttempt
import json
from django.views.decorators.csrf import ensure_csrf_cookie
from django.middleware.csrf import get_token
import random

def get_identifier(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    return x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')

@ensure_csrf_cookie
def captcha_page(request):
    # get_token(request)   # ensures csrftoken cookie is set
    return render(request, 'captcha_page.html')

def protected_page(request):
    if not request.session.get("captcha_passed", False):
        return redirect('/')
    return render(request, 'protected_page.html')

def first_page(request):
    # get_token(request) 
    
    return render(request, 'first_page.html')
@csrf_protect
@require_http_methods(["GET"])
def get_captcha(request):
    identifier = get_identifier(request)
    attempt, _ = CaptchaAttempt.get_or_create_for_identifier(identifier)
    
    if attempt.is_blocked and attempt.blocked_until > timezone.now():
        return JsonResponse({'status': 'blocked'}, status=403)
    
    difficulty = determine_difficulty(attempt.attempts)
    challenge = generate_challenge(difficulty)

    captcha_id = random.randint(1000, 9999)  # temporary unique ID
    request.session['captcha'] = {
        'id': captcha_id,
        'correct_answer': challenge['correct_answer'],
        'expires_at': (timezone.now() + timezone.timedelta(minutes=5)).isoformat()
    }
    
    return JsonResponse({
        'id': captcha_id,
        'difficulty': difficulty,
        'time_limit': 60 if difficulty >= 2 else None,
        **challenge
    })


def determine_difficulty(attempts):
    if attempts >= 3:   # 3rd + 4th attempt → hardest level
        return 3
    if attempts >= 2:   # 2nd attempt → medium
        return 2
    return 1

def generate_challenge(difficulty):
    params = {
        1: {'actors': 5, 'speed': 1.0},
        2: {'actors': 7, 'speed': 1.5},
        3: {'actors': 10, 'speed': 1.5},
    }[difficulty]
    
    scene = random.choice(['room', 'park', 'street', 'cafe'])
    colors = ['red', 'green', 'blue', 'yellow','cyan','lime','orange'] #changed here
    actors = [
        {
            'color': random.choice(colors),
            'delay': i * 0.5,
            'speed': round(random.uniform(0.8, 1.2) * params['speed'], 2) , #we changed here
            'object': f"item_{random.choice(colors)}" if i == 0 else None
        } 
        for i in range(params['actors'])
    ]
    
    question = random.choice([
    "What color was the item?",
    "Which color appeared last?",
    "What was the object’s color?",
])

    correct = next(a['object'].split('_')[1] if a['object'] else a['color'] for a in actors if a['object'] or question.endswith('first?'))
    
    return {
        'scene': scene,
        'question': question,
        'options': random.sample(colors, 3) + [correct],
        'correct_answer': correct,
        'animation_data': {'actors': actors},
    }

@csrf_protect
@require_http_methods(["POST"])
def submit_captcha_answer(request):
    try:
        data = json.loads(request.body)
        identifier = get_identifier(request)
        attempt, _ = CaptchaAttempt.get_or_create_for_identifier(identifier)
        
        if attempt.is_blocked:
            return JsonResponse({'status': 'blocked'}, status=403)
        
        # ⬇️ replaced DB lookup with session read
        challenge = request.session.get('captcha')
        if not challenge or data.get('id') != challenge.get('id'):
            return JsonResponse({'status': 'invalid'}, status=400)

        # ⬇️ expiry check
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
        # ⬇️ instead of challenge.used = True, just clear session
        if 'captcha' in request.session:
            del request.session['captcha']
        
        return JsonResponse({
            'status': status,
            'attempts': attempt.attempts,
            'difficulty': determine_difficulty(attempt.attempts)
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
