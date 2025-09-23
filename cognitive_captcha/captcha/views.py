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
import os
from django.conf import settings

def get_identifier(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    return x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')

@ensure_csrf_cookie
def captcha_page(request):
    return render(request, 'captcha_page.html')

def protected_page(request):
    if not request.session.get("captcha_passed", False):
        return redirect('/')
    return render(request, 'protected_page.html')

def first_page(request):
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
        **challenge
    })


def determine_difficulty(attempts):
    if attempts >= 3:
        return 3
    if attempts >= 2:
        return 2
    return 1

def generate_challenge(difficulty):
    # Define different animations for different difficulty levels
    animations = {
        1: 'bouncing_ball.json',  # Simple animation
        2: 'multiple_bouncing_balls.json',  # Medium complexity
        3: 'complex_animation.json'  # Complex animation
    }
    
    # For now, use the sample.json for all difficulties
    # You can replace this with different animations later
    animation_file = os.path.join(settings.BASE_DIR, 'captcha', 'static', 'sample.json')
    
    try:
        with open(animation_file, 'r') as f:
            animation_data = json.load(f)
    except FileNotFoundError:
        # Fallback to a simple animation data structure if file not found
        animation_data = {"v": "5.12.2", "fr": 30, "ip": 0, "op": 90, "w": 400, "h": 300, "nm": "Sample Animation"}
    
    # Create questions that match the animation content
    if "bouncy ball" in animation_data.get("nm", "").lower():
        # Questions for bouncing ball animation
        question, correct_answer = generate_bouncing_ball_questions()
        options = generate_options(correct_answer, ["1", "2", "3", "4", "5"])
    else:
        # Default questions
        question = "How many times did the main object bounce?"
        correct_answer = "2"
        options = ["1", "2", "3", "4"]
    
    return {
        'question': question,
        'options': options,
        'correct_answer': correct_answer,
        'animation_data': animation_data,  # This is the Lottie JSON data
    }

def generate_bouncing_ball_questions():
    """Generate questions specific to bouncing ball animations"""
    question_types = [
        ("How many times did the ball bounce?", "2"),
        ("What color was the bouncing ball?", "purple"),
        ("What was the main object in the animation?", "ball"),
        ("Did the ball bounce on a trampoline or floor?", "trampoline")
    ]
    return random.choice(question_types)

def generate_options(correct_answer, possible_options):
    """Generate multiple choice options including the correct answer"""
    options = [correct_answer]
    
    # Add 3 random options that are not the correct answer
    while len(options) < 4:
        random_option = random.choice(possible_options)
        if random_option != correct_answer and random_option not in options:
            options.append(random_option)
    
    # Shuffle the options
    random.shuffle(options)
    return options

@csrf_protect
@require_http_methods(["POST"])
def submit_captcha_answer(request):
    try:
        data = json.loads(request.body)
        identifier = get_identifier(request)
        attempt, _ = CaptchaAttempt.get_or_create_for_identifier(identifier)
        
        if attempt.is_blocked:
            return JsonResponse({'status': 'blocked'}, status=403)
        
        # replaced DB lookup with session read
        challenge = request.session.get('captcha')
        if not challenge or data.get('id') != challenge.get('id'):
            return JsonResponse({'status': 'invalid'}, status=400)

        # expiry check
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
        # instead of challenge.used = True, just clear session
        if 'captcha' in request.session:
            del request.session['captcha']
        
        return JsonResponse({
            'status': status,
            'attempts': attempt.attempts,
            'difficulty': determine_difficulty(attempt.attempts)
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)