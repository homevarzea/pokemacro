import os
import sys
import threading
import time
import cv2
import pyautogui
import keyboard
from modules.snipper import get_crop_area
from modules.utils import save_to_file, load_from_file, capture_screen, extract_text, play_alert_sound
from modules.key_mapper import convert_key_name
import easyocr
import numpy as np
from datetime import datetime, time as dt_time

# Force unbuffered output so logs appear immediately
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Try to import win32api - it's needed for reliable mouse click detection
try:
    import win32api
    import win32con
    WIN32_AVAILABLE = True
    print("[DEBUG] win32api successfully imported")
except ImportError:
    WIN32_AVAILABLE = False
    print("[DEBUG] win32api not available")

# Try to import pynput as a fallback
try:
    from pynput import mouse as pynput_mouse
    PYNPUT_AVAILABLE = True
    print("[DEBUG] pynput successfully imported")
except ImportError:
    PYNPUT_AVAILABLE = False
    print("[DEBUG] pynput not available")


auto_combo_enabled = False
anti_logout_enabled = False
alert_enabled = False
healing_enabled = False
combo_event = threading.Event()
combo_running = False
cached_auto_catch_config = None
current_combo_hook = None
stop_hook = None
auto_catch_hook = None 
auto_catch_enabled = False
pokeball_trigger_key = None
auto_catch_enabled = False

# Global variables to control the coordinate tracking
mouse_tracking_enabled = False
mouse_coords = {'x': 0, 'y': 0}
mouse_tracking_thread = None

# Add these globals at the top of the file
auto_revive_enabled = False
auto_revive_hook = None

def execute_move(move_list):
    print(move_list)
    for move in move_list:
        if move.get('delay'):
            # Handle delay
            delay = float(move.get('delay')) / 1000.0
            time.sleep(delay)
            
        elif move.get('autoCatch'):
            # Handle autoCatch
            pass
            
        elif move.get('mouseClick'):
            # Handle mouse click
            mouse_click = move.get('mouseClick')
            button = mouse_click.get('button', 'left')
            x = mouse_click.get('x', 0)
            y = mouse_click.get('y', 0)
            
            pyautogui.moveTo(x, y)
            if button == 'left':
                pyautogui.click()
            else:
                pyautogui.rightClick()
            
        elif move.get('hotkey'):
            # Handle hotkey press
            hotkey = move.get('hotkey')
            key_name = hotkey.get('keyName')
            if key_name:
                # Convert frontend key name to Python keyboard library format
                python_key_name = convert_key_name(key_name)
                print(f"Pressing hotkey: {key_name} -> {python_key_name}")
                try:
                    keyboard.press_and_release(python_key_name)
                    time.sleep(0.1)  # Small delay after key press
                except Exception as e:
                    print(f"Error pressing key '{python_key_name}': {str(e)}")
                    # Try the original key name as fallback
                    try:
                        keyboard.press_and_release(key_name)
                        print(f"Fallback successful with original key name: {key_name}")
                    except Exception as e2:
                        print(f"Both key formats failed: {str(e2)}")
            
        elif move.get('skillName') and not move.get('hotkey'):
            # Handle skillName without hotkey
            skill_name = move.get('skillName')
            print(f"Processing skill without hotkey: {skill_name}")
            
            try:
                keybindings = load_from_file('keybindings.json')
                if keybindings and skill_name in keybindings:
                    key_data = keybindings[skill_name]
                    key_name = key_data.get('keyName')
                    key_number = key_data.get('keyNumber')
                    if key_name and key_number is not None:
                        print(f"Found keybinding for {skill_name}: {key_name} ({key_number})")
                        # Convert frontend key name to Python keyboard library format
                        python_key_name = convert_key_name(key_name)
                        print(f"Converting key: {key_name} -> {python_key_name}")
                        try:
                            keyboard.press_and_release(python_key_name)
                            time.sleep(0.1)
                        except Exception as e:
                            print(f"Error pressing key '{python_key_name}': {str(e)}")
                            # Try the original key name as fallback
                            try:
                                keyboard.press_and_release(key_name)
                                print(f"Fallback successful with original key name: {key_name}")
                            except Exception as e2:
                                print(f"Both key formats failed: {str(e2)}")
                    else:
                        print(f"Invalid keybinding format for skill: {skill_name}")
                else:
                    print(f"No keybinding found for skill: {skill_name}")
            except Exception as e:
                print(f"Error loading keybindings for skill {skill_name}: {str(e)}")
        
        # Skip malformed entries
        elif move.get('id') and not any([move.get('hotkey'), move.get('skillName'), move.get('delay'), move.get('mouseClick'), move.get('autoCatch')]):
            print(f"Skipping malformed entry with id: {move.get('id')}")
            continue

def toggle_anti_logout():
    global anti_logout_enabled
    anti_logout_enabled = not anti_logout_enabled

    def run():
        while anti_logout_enabled:
            with pyautogui.hold('ctrl'):
                pyautogui.press('a')
                time.sleep(1)
                pyautogui.press('d')
            time.sleep(5)

    threading.Thread(target=run, daemon=True).start()
    return f"Keyboard events {'enabled' if anti_logout_enabled else 'disabled'}"

def toggle_alert():
    global alert_enabled
    alert_enabled = not alert_enabled

    def run():
        # try:
        iteration = 0
        
        while alert_enabled:
            alert_config = load_from_file('alertConfig.json')
            offset_x = int(alert_config['fields']['offset_x']['value'])
            offset_y = int(alert_config['fields']['offset_y']['value'])
            x_length = int(alert_config['fields']['x_length']['value'])
            y_length = int(alert_config['fields']['y_length']['value'])

            battle_box = (offset_x, offset_y, x_length, y_length)
            # Capture the battle box region
            screenshot = capture_screen(bbox=battle_box)

            iteration += 1

            # Extract text from the screenshot
            text = extract_text(screenshot)

            # Split the text into lines and check for matches
            should_play_sound = False
            line_to_print = ''
            for line in text.splitlines():
                line_stripped = line.strip()
                if line_stripped:
                    line_has_any_target = False
                    for target in alert_config['hunt']['list']:
                        if target in line_stripped:
                            line_has_any_target = True
                    if line_has_any_target == False:
                        line_to_print = line_stripped
                        should_play_sound = True
                
            if should_play_sound:
                play_alert_sound()
            
            del screenshot
            del text

            time.sleep(0.5)
        # except Exception as e:
        #     print(f"Error running alert: {str(e)}")

    threading.Thread(target=run, daemon=True).start()
    return {
        "alert_enabled": alert_enabled,
        "message": f"Alert {'enabled' if alert_enabled else 'disabled'}"
    }

def toggle_healing():
    global healing_enabled
    healing_enabled = not healing_enabled

    def run():
        reader = easyocr.Reader(['en'])
        iteration = 0
        while healing_enabled:
            heal_config = load_from_file('healConfig.json')
            keybindings = load_from_file('keybindings.json')

            ph_x_start = int(heal_config['fields']['poke_heal_x_start']['value'])
            ph_x_end = int(heal_config['fields']['poke_heal_x_end']['value'])
            ph_y_start = int(heal_config['fields']['poke_heal_y_start']['value'])
            ph_y_end = int(heal_config['fields']['poke_heal_y_end']['value'])

            pokemon_life_box = (ph_x_start, ph_y_start, ph_x_end, ph_y_end)
            ph_hotkey = keybindings['Poke Heal']['keyName']
            ph_cooldown = int(heal_config['fields']['poke_heal_cooldown']['value'])
            ph_percent_limit = int(heal_config['fields']['poke_heal_percent_limit']['value']) / 100


            screenshot = capture_screen(bbox=pokemon_life_box)

            # save_debug_image(screenshot, iteration)
            iteration += 1

            text_array = reader.readtext(np.array(screenshot), detail=0)
        
            if len(text_array) == 2:
                health = int(text_array[0])
                total_health = int(text_array[1])
                if health / total_health <= ph_percent_limit:
                    # Convert frontend key name to Python keyboard library format
                    python_key_name = convert_key_name(ph_hotkey)
                    print(f"Healing: pressing {ph_hotkey} -> {python_key_name}")
                    try:
                        keyboard.press_and_release(python_key_name)
                    except Exception as e:
                        print(f"Error pressing healing key '{python_key_name}': {str(e)}")
                        # Try the original key name as fallback
                        try:
                            keyboard.press_and_release(ph_hotkey)
                        except Exception as e2:
                            print(f"Both healing key formats failed: {str(e2)}")
                    time.sleep(ph_cooldown)
                
            del screenshot
            
            # Wait for a short time before capturing the screen again
            time.sleep(0.5)
        del reader

    threading.Thread(target=run, daemon=True).start()
    return {
        "healing_enabled": healing_enabled,
        "message": f"Healing {'enabled' if healing_enabled else 'disabled'}"
    }

def toggle_auto_combo(trigger_key, current_combo, stop_key='home'):
    global auto_combo_enabled, current_combo_hook, stop_hook
    auto_combo_enabled = not auto_combo_enabled
    
    # Convert stop_key in case it's a frontend key name
    python_stop_key = convert_key_name(stop_key)

    if auto_combo_enabled:
        if current_combo_hook is not None:
            keyboard.unhook(current_combo_hook)
        current_combo_hook = keyboard.on_press_key(trigger_key, lambda event: run_combo(current_combo))
        
        if stop_hook is not None:
            keyboard.unhook(stop_hook)
        stop_hook = keyboard.on_press_key(python_stop_key, lambda event: stop_function(combo_event))
    else:
        if current_combo_hook is not None:
            keyboard.unhook(current_combo_hook)
            current_combo_hook = None
        if stop_hook is not None:
            keyboard.unhook(stop_hook)
            stop_hook = None

    return f"Keyboard events {'enabled' if auto_combo_enabled else 'disabled'}"

def update_current_combo(trigger_key, current_combo):
    global current_combo_hook
    if current_combo_hook is not None:
        keyboard.unhook(current_combo_hook)
        current_combo_hook = None

    # Ensure the moveList structure is preserved
    current_combo['moveList'] = [
        {
            **move,
            'hotkey': move.get('hotkey', None)  # Preserve hotkey structure
        }
        for move in current_combo.get('moveList', [])
    ]

    current_combo_hook = keyboard.on_press_key(trigger_key, lambda event: run_combo(current_combo))
    return current_combo

def run_combo(current_combo):
    global combo_running
    if combo_running:
        print("Combo already in progress; ignoring trigger.")
        return
    combo_event.clear()
    combo_running = True
    threading.Thread(target=fire_combo, args=(current_combo,), daemon=True).start()

def fire_combo(current_combo):
    global combo_running
    if auto_combo_enabled:
        execute_move(current_combo.get('moveList', []))
    combo_running = False

def stop_function(event):
    global combo_running
    event.clear()    
    event.set()
    combo_running = False

def execute_key_action(event, key):
    if event.is_set():
        return False
    # Convert frontend key name to Python keyboard library format
    python_key_name = convert_key_name(key)
    try:
        keyboard.press_and_release(python_key_name)
    except Exception as e:
        print(f"Error pressing key '{python_key_name}': {str(e)}")
        # Try the original key name as fallback
        try:
            keyboard.press_and_release(key)
        except Exception as e2:
            print(f"Both key formats failed for '{key}': {str(e2)}")
    return True

def save_config(config, filename):
    return save_to_file(config, filename)

def load_config(filename):
    return load_from_file(filename)

def execute_crop_area():
    try:
        # Get the crop area and full screenshot from the snipper
        x, y, w, h, full_screenshot = get_crop_area()
        cropped_img = full_screenshot.crop((x, y, x + w, y + h))
        
        # Ensure the 'images' folder exists
        images_folder = "images"
        if not os.path.exists(images_folder):
            os.makedirs(images_folder)
        
        # Generate a unique filename using a timestamp
        timestamp = int(time.time())
        output_filename = f"cropped_{timestamp}.png"
        output_path = os.path.join(images_folder, output_filename)
        
        cropped_img.save(output_path)
        
        return {"message": "Cropping completed", "image": output_path}
    except Exception as e:
        return {"message": f"Error during cropping: {str(e)}"}
    
def toggle_auto_catch(config_override=None):
    global auto_catch_enabled, auto_catch_hook, cached_auto_catch_config, pokeball_trigger_key

    # Load the current auto catch configuration from file and store it in our cache
    config = config_override if isinstance(config_override, dict) else load_from_file("autocatch.json")
    if config.get('mode', 'game') == 'game':
        from modules import game_client
        try:
            if game_client.status().get('enabled'):
                result = game_client.command('stop')
            else:
                result = game_client.command('start', {
                    'ballId': config.get('ballId', 3552),
                    'ballName': config.get('ballName', 'Ultra Ball' if config.get('ballId', 3552) == 3552 else ''),
                    'catchIntervalMs': config.get('catchIntervalMs', 500),
                    'pokemonNames': config.get('pokemonNames', ['Oddish', 'Gloom']),
                })
            auto_catch_enabled = bool(result.get('enabled'))
            return {'auto_catch_enabled': auto_catch_enabled, 'game': result,
                    'message': f"Auto Catch {'enabled' if auto_catch_enabled else 'disabled'}"}
        except Exception as error:
            auto_catch_enabled = False
            return {'auto_catch_enabled': False, 'error': str(error), 'message': str(error)}

    # Disable an existing image hook even when its settings were edited.
    if auto_catch_enabled:
        if auto_catch_hook is not None:
            keyboard.unhook(auto_catch_hook)
            auto_catch_hook = None
        auto_catch_enabled = False
        return {'auto_catch_enabled': False, 'message': 'Auto Catch disabled'}
    if not config or not config.get("hotkey"):
        print("No hotkey set for Auto Catch.")
        return {
            "auto_catch_enabled": auto_catch_enabled,
            "message": "No hotkey set for Auto Catch."
        }
    cached_auto_catch_config = config  # Store config for future use

    # Load keybindings from keybindings.json and get the "Pokeball" hotkey
    keybindings = load_from_file("keybindings.json")
    if not keybindings or "Pokeball" not in keybindings or not keybindings["Pokeball"].get("keyName"):
        print("No Pokeball hotkey set in keybindings.json.")
        return {
            "auto_catch_enabled": auto_catch_enabled,
            "message": "No Pokeball hotkey set in keybindings.json."
        }
    pokeball_trigger_key = keybindings["Pokeball"]["keyName"]

    # Use the hotkey from autocatch config for toggling
    trigger_key = config.get("hotkey")
    
    # Convert frontend key names to Python keyboard library format
    python_trigger_key = convert_key_name(trigger_key)
    # Store the converted pokeball key globally for use in locate_and_interact_with_images
    pokeball_trigger_key = convert_key_name(pokeball_trigger_key)

    auto_catch_enabled = not auto_catch_enabled

    if auto_catch_enabled:
        if auto_catch_hook is not None:
            keyboard.unhook(auto_catch_hook)
        auto_catch_hook = keyboard.on_press_key(python_trigger_key, lambda event: locate_and_interact_with_images())
        print(f"Auto Catch enabled. Press '{trigger_key.upper()}' to start searching for images.")
    else:
        if auto_catch_hook is not None:
            keyboard.unhook(auto_catch_hook)
            auto_catch_hook = None
        print("Auto Catch disabled.")

    return {
        "auto_catch_enabled": auto_catch_enabled,
        "message": f"Auto Catch {'enabled' if auto_catch_enabled else 'disabled'}"
    }

def locate_image_opencv(template_path, threshold=0.9):
    screenshot = pyautogui.screenshot()
    screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    
    template = cv2.imread(template_path, cv2.IMREAD_COLOR)
    if template is None:
        raise ValueError(f"Não foi possível carregar o template: {template_path}")
    h, w, _ = template.shape

    # Executa o match template
    res = cv2.matchTemplate(screenshot_cv, template, cv2.TM_CCOEFF_NORMED)
    loc = np.where(res >= threshold)

    # Armazena todos os matches encontrados
    matches = []
    for pt in zip(*loc[::-1]):
        matches.append((pt[0], pt[1], w, h))
    return matches

def process_image(image_path, control_lock, stop_time, trigger_key):
    shiny_template = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if shiny_template is None:
        return
    template_hsv = cv2.cvtColor(shiny_template, cv2.COLOR_BGR2HSV)
    template_hist = cv2.calcHist([template_hsv], [0], None, [180], [0, 180])
    cv2.normalize(template_hist, template_hist, 0, 1, cv2.NORM_MINMAX)

    start_time = time.time()
    delay = 0.05  

    while time.time() - start_time < stop_time:
        try:
            matches = locate_image_opencv(image_path, threshold=0.9)
        except Exception as e:
            time.sleep(delay)
            continue

        if matches:
            for (x, y, w, h) in matches:
                x, y, w, h = int(x), int(y), int(w), int(h)
                
                screenshot = pyautogui.screenshot(region=(x, y, w, h))
                region_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                
                region_hsv = cv2.cvtColor(region_cv, cv2.COLOR_BGR2HSV)
                region_hist = cv2.calcHist([region_hsv], [0], None, [180], [0, 180])
                cv2.normalize(region_hist, region_hist, 0, 1, cv2.NORM_MINMAX)
                
                correlation = cv2.compareHist(template_hist, region_hist, cv2.HISTCMP_CORREL)
                if correlation >= 0.95:
                    with control_lock:
                        center_x = x + w // 2
                        center_y = y + h // 2
                        pyautogui.moveTo(center_x, center_y)
                        keyboard.press(trigger_key)
                        keyboard.release(trigger_key)
                        pyautogui.click(center_x, center_y)
                    break

        time.sleep(delay)

    print(f"Busca pela imagem {os.path.basename(image_path)} encerrada após {stop_time} segundos.")


def locate_and_interact_with_images():
    global cached_auto_catch_config, pokeball_trigger_key

    if not cached_auto_catch_config or "selectedImages" not in cached_auto_catch_config or not cached_auto_catch_config["selectedImages"]:
        print("No selected images configured in autocatch.json.")
        return

    selected_images = cached_auto_catch_config["selectedImages"] 
    images_path = os.path.join(os.getcwd(), "images")
    if not os.path.exists(images_path):
        print("Images folder does not exist.")
        return

    control_lock = threading.Lock()
    stop_time = 5 

    for img in selected_images:
        filename = img.get("filename")
        if not filename:
            continue
        long_image_path = os.path.join(images_path, filename)
        if not os.path.exists(long_image_path):
            print(f"File {filename} does not exist at the specified path.")
            continue

        t = threading.Thread(
            target=process_image, 
            args=(long_image_path, control_lock, stop_time, pokeball_trigger_key), 
            daemon=True
        )
        t.start()
        print(f"Started task for {filename} (will stop after {stop_time} seconds)")

    print("All image search tasks started in parallel.")

def toggle_mouse_tracking():
    """Toggle the mouse coordinate tracking on/off"""
    global mouse_tracking_enabled, mouse_tracking_thread, mouse_coords
    
    print(f"[DEBUG] Toggling mouse tracking. Current state: {mouse_tracking_enabled}")
    mouse_tracking_enabled = not mouse_tracking_enabled
    
    if mouse_tracking_enabled:
        print("[DEBUG] Starting mouse tracking...")
        # Clear previous coordinates when starting tracking
        mouse_coords = {'x': 0, 'y': 0}
        print("[DEBUG] Cleared previous mouse coordinates")
        
        # Start a new thread to monitor mouse clicks
        if mouse_tracking_thread is None or not mouse_tracking_thread.is_alive():
            mouse_tracking_thread = threading.Thread(target=monitor_mouse, daemon=True)
            mouse_tracking_thread.start()
            print("[DEBUG] Mouse tracking thread started")
    else:
        print("[DEBUG] Mouse tracking disabled")
            
    return {
        "tracking_enabled": mouse_tracking_enabled,
        "message": f"Mouse tracking {'enabled' if mouse_tracking_enabled else 'disabled'}"
    }

def monitor_mouse():
    """Monitor mouse clicks and Enter key presses"""
    global mouse_tracking_enabled, mouse_coords
    
    print(f"[DEBUG] Starting mouse monitoring (win32: {WIN32_AVAILABLE}, pynput: {PYNPUT_AVAILABLE})")
    
    # Method 1: Try using pynput listener (most reliable cross-platform)
    if PYNPUT_AVAILABLE:
        mouse_listener = None
        click_detected = False
        
        def on_click(x, y, button, pressed):
            nonlocal click_detected
            global mouse_tracking_enabled, mouse_coords
            
            if pressed and not click_detected:  # Only on press, not release
                mouse_coords['x'] = x
                mouse_coords['y'] = y
                print(f"[DEBUG] Captured mouse position via pynput click: {mouse_coords}")
                mouse_tracking_enabled = False
                click_detected = True
                return False  # Stop listener
        
        try:
            mouse_listener = pynput_mouse.Listener(on_click=on_click)
            mouse_listener.start()
            print("[DEBUG] pynput mouse listener started")
            
            # Monitor for Enter key and check if tracking is still enabled
            while mouse_tracking_enabled and not click_detected:
                try:
                    # Check for Enter key press
                    if keyboard.is_pressed('enter'):
                        current_pos = pyautogui.position()
                        mouse_coords['x'] = current_pos[0]
                        mouse_coords['y'] = current_pos[1]
                        print(f"[DEBUG] Captured mouse position via Enter key: {mouse_coords}")
                        mouse_tracking_enabled = False
                        break
                    
                    time.sleep(0.05)
                except Exception as e:
                    print(f"[DEBUG] Error checking Enter key: {e}")
                    time.sleep(0.1)
            
            if mouse_listener:
                mouse_listener.stop()
                
        except Exception as e:
            print(f"[DEBUG] Error with pynput: {e}")
            # Fall back to win32api or manual method
            pass
    
    # Method 2: Fallback to win32api if pynput failed
    if mouse_tracking_enabled and WIN32_AVAILABLE:
        print("[DEBUG] Using win32api fallback method")
        last_click_time = 0
        
        while mouse_tracking_enabled:
            try:
                # Get current mouse position
                current_pos = pyautogui.position()
                
                # Check for Enter key press
                if keyboard.is_pressed('enter'):
                    mouse_coords['x'] = current_pos[0]
                    mouse_coords['y'] = current_pos[1]
                    print(f"[DEBUG] Captured mouse position via Enter key: {mouse_coords}")
                    mouse_tracking_enabled = False
                    break
                
                # Check for mouse click
                left_button_state = win32api.GetAsyncKeyState(0x01)  # Left mouse button
                current_time = time.time()
                
                if left_button_state < 0 and current_time - last_click_time > 0.5:
                    mouse_coords['x'] = current_pos[0]
                    mouse_coords['y'] = current_pos[1]
                    print(f"[DEBUG] Captured mouse position via win32api click: {mouse_coords}")
                    mouse_tracking_enabled = False
                    break
                
                time.sleep(0.05)
                
            except Exception as e:
                print(f"[DEBUG] Error in win32api method: {e}")
                time.sleep(0.1)
    
    # Method 3: Last resort - Enter key only
    if mouse_tracking_enabled:
        print("[DEBUG] Using Enter key only method (last resort)")
        while mouse_tracking_enabled:
            try:
                if keyboard.is_pressed('enter'):
                    current_pos = pyautogui.position()
                    mouse_coords['x'] = current_pos[0]
                    mouse_coords['y'] = current_pos[1]
                    print(f"[DEBUG] Captured mouse position via Enter key: {mouse_coords}")
                    mouse_tracking_enabled = False
                    break
                time.sleep(0.05)
            except Exception as e:
                print(f"[DEBUG] Error in Enter key method: {e}")
                time.sleep(0.1)
    
    print("[DEBUG] Mouse monitoring stopped")

def get_mouse_coords():
    """Return the current tracked mouse coordinates"""
    print(f"[DEBUG] get_mouse_coords called, returning: {mouse_coords}")
    return mouse_coords

def clear_mouse_coords():
    """Clear the stored mouse coordinates"""
    global mouse_coords
    mouse_coords = {'x': 0, 'y': 0}
    print(f"[DEBUG] Mouse coordinates cleared")
    return {"message": "Mouse coordinates cleared"}

def toggle_auto_revive():
    """Toggle the auto revive functionality on/off"""
    global auto_revive_enabled, auto_revive_hook
    
    # FORCE LOG - This should ALWAYS appear
    print("="*50)
    print("TOGGLE AUTO REVIVE FUNCTION CALLED!")
    print("="*50)
    
    print(f"[Auto Revive] ==> Toggling auto revive. Current state: {auto_revive_enabled}")
    
    # Always unhook the existing hook if one exists
    if auto_revive_hook is not None:
        print("[Auto Revive] ==> Unhooking existing auto revive hook")
        try:
            keyboard.unhook(auto_revive_hook)
            print("[Auto Revive] ==> Successfully unhooked existing hook")
        except Exception as e:
            print(f"[Auto Revive] ==> ERROR unhooking: {str(e)}")
        auto_revive_hook = None
    
    # Toggle the enabled state
    auto_revive_enabled = not auto_revive_enabled
    print(f"[Auto Revive] ==> New state: {auto_revive_enabled}")
    
    if not auto_revive_enabled:
        print("[Auto Revive] ==> Auto Revive disabled, returning")
        return {
            "auto_revive_enabled": auto_revive_enabled,
            "message": "Auto Revive disabled"
        }
    
    # Load the latest config
    print("[Auto Revive] ==> Loading autorevive.json config...")
    config = load_from_file("autorevive.json")
    print(f"[Auto Revive] ==> Loaded config: {config}")
    
    if not config:
        print("[Auto Revive] ==> ERROR: Config file not found or empty")
        auto_revive_enabled = False
        return {
            "auto_revive_enabled": auto_revive_enabled,
            "message": "ERROR: autorevive.json not found"
        }
    
    keybind = config.get("keybind")
    if not keybind:
        print("[Auto Revive] ==> ERROR: No keybind set in config")
        auto_revive_enabled = False
        return {
            "auto_revive_enabled": auto_revive_enabled,
            "message": "ERROR: No hotkey set for Auto Revive"
        }
    
    position = config.get("position", {})
    if not position or position.get("x", 0) == 0 and position.get("y", 0) == 0:
        print("[Auto Revive] ==> ERROR: No position set in config")
        auto_revive_enabled = False
        return {
            "auto_revive_enabled": auto_revive_enabled,
            "message": "ERROR: No revive position set"
        }
    
    # Set up a new hook if enabled
    print(f"[Auto Revive] ==> Setting up hook for key: '{keybind}'")
    
    # Convert frontend key name to Python keyboard library format
    python_trigger_key = convert_key_name(keybind)
    print(f"[Auto Revive] ==> Converted key: '{keybind}' -> '{python_trigger_key}'")
    
    try:
        # Create a wrapper function that loads fresh config each time
        def auto_revive_handler(event):
            try:
                print(f"[Auto Revive] ==> KEY PRESSED! Triggered by: {keybind}")
                print(f"[Auto Revive] ==> Event details: {event}")
                fresh_config = load_from_file("autorevive.json")
                if fresh_config:
                    print(f"[Auto Revive] ==> Executing with fresh config: {fresh_config}")
                    perform_auto_revive(fresh_config)
                else:
                    print("[Auto Revive] ==> ERROR: Could not load config for execution")
            except Exception as e:
                print(f"[Auto Revive] ==> ERROR in handler: {str(e)}")
        
        try:
            # Try multiple hook methods
            print(f"[Auto Revive] ==> Attempting to register hook for '{python_trigger_key}'")
            
            # Method 1: on_press_key (specific key)
            auto_revive_hook = keyboard.on_press_key(python_trigger_key, auto_revive_handler)
            print(f"[Auto Revive] ==> Method 1 successful: {auto_revive_hook}")
            
        except Exception as e:
            print(f"[Auto Revive] ==> Method 1 failed, trying Method 2: {str(e)}")
            try:
                # Method 2: on_press with filter
                def filtered_handler(event):
                    if event.name == python_trigger_key:
                        auto_revive_handler(event)
                
                auto_revive_hook = keyboard.on_press(filtered_handler)
                print(f"[Auto Revive] ==> Method 2 successful: {auto_revive_hook}")
                
            except Exception as e2:
                print(f"[Auto Revive] ==> Both methods failed: {str(e2)}")
                auto_revive_enabled = False
                return {
                    "auto_revive_enabled": auto_revive_enabled,
                    "message": f"ERROR setting up Auto Revive: {str(e2)}"
                }
        print(f"[Auto Revive] ==> SUCCESS! Hook registered for '{python_trigger_key}'")
        print(f"[Auto Revive] ==> Auto Revive enabled! Press '{keybind.upper()}' to revive.")
        
        # Test if the hook is actually registered
        print(f"[Auto Revive] ==> Hook object: {auto_revive_hook}")
        
    except Exception as e:
        print(f"[Auto Revive] ==> ERROR setting up hook for '{python_trigger_key}': {str(e)}")
        auto_revive_enabled = False
        return {
            "auto_revive_enabled": auto_revive_enabled,
            "message": f"ERROR setting up Auto Revive: {str(e)}"
        }
    
    return {
        "auto_revive_enabled": auto_revive_enabled,
        "message": f"Auto Revive enabled! Press '{keybind.upper()}' to revive."
    }

def perform_auto_revive(config):
    """Perform the auto revive action following the step-by-step timeline"""
    try:
        print(f"[Auto Revive] Starting with config: {config}")
        
        # Get the stored revive position
        position = config.get("position", {})
        revive_x = position.get("x", 0)
        revive_y = position.get("y", 0)
        
        if revive_x == 0 and revive_y == 0:
            print("[Auto Revive] ERROR: No valid position set")
            return False
        
        # Get delays from config (with fallback defaults for backward compatibility)
        delays = config.get("delays", {})
        after_move = delays.get("afterMove", 100) / 1000.0  # Convert to seconds
        after_remove_pokemon = delays.get("afterRemovePokemon", 200) / 1000.0
        after_use_revive = delays.get("afterUseRevive", 300) / 1000.0
        after_release_pokemon = delays.get("afterReleasePokemon", 150) / 1000.0
        
        # Get click configuration (with fallback defaults)
        click_config = config.get("clickConfig", {})
        remove_click_type = click_config.get("removeClick", "right")  # "right" or "left"
        release_click_type = click_config.get("releaseClick", "left")  # "right" or "left"
        
        # Check if there's a specific release position configured
        release_position = click_config.get("releasePosition")
        use_same_position = release_position is None
        
        print(f"[Auto Revive] Starting process with target position ({revive_x}, {revive_y})")
        print(f"[Auto Revive] Delays: Move={after_move*1000}ms, Remove={after_remove_pokemon*1000}ms, Revive={after_use_revive*1000}ms, Release={after_release_pokemon*1000}ms")
        print(f"[Auto Revive] Click config: Remove={remove_click_type.upper()}, Release={release_click_type.upper()}")
        
        # Get the current mouse position
        current_x, current_y = pyautogui.position()
        print(f"[Auto Revive] Current position: ({current_x}, {current_y})")
        
        # STEP 1: Move to revive position
        print(f"[Auto Revive] Step 1: Moving to revive position...")
        pyautogui.moveTo(revive_x, revive_y, duration=0.1)  # Quick smooth movement
        time.sleep(after_move)  # Wait after moving
        
        # STEP 2: Remove pokemon (configurable click)
        print(f"[Auto Revive] Step 2: Removing pokemon ({remove_click_type} click)...")
        if remove_click_type.lower() == "right":
            pyautogui.rightClick()
        else:
            pyautogui.leftClick()
        time.sleep(after_remove_pokemon)  # Wait after removing pokemon
        
        # STEP 3: Use revive (press key)
        print(f"[Auto Revive] Step 3: Using revive...")
        keybindings = load_from_file("keybindings.json")
        if not keybindings or "Revive" not in keybindings:
            print("[Auto Revive] ERROR: Revive keybinding not found in keybindings.json")
            return False

        # Get the keyName for Revive
        revive_key = keybindings["Revive"].get("keyName")
        if not revive_key:
            print("[Auto Revive] ERROR: Revive keyName is missing in keybindings.json")
            return False

        # Convert frontend key name to Python keyboard library format
        python_revive_key = convert_key_name(revive_key)
        print(f"[Auto Revive] Pressing revive key: {revive_key} -> {python_revive_key}")
        
        try:
            keyboard.press_and_release(python_revive_key)
            print(f"[Auto Revive] Successfully pressed key: {python_revive_key}")
        except Exception as e:
            print(f"[Auto Revive] Error pressing revive key '{python_revive_key}': {str(e)}")
            # Try the original key name as fallback
            try:
                keyboard.press_and_release(revive_key)
                print(f"[Auto Revive] Fallback successful with original revive key: {revive_key}")
            except Exception as e2:
                print(f"[Auto Revive] Both revive key formats failed: {str(e2)}")
                return False
        
        time.sleep(after_use_revive)  # Wait after using revive
        
        # STEP 4: Release pokemon (configurable click to confirm)
        print(f"[Auto Revive] Step 4: Releasing pokemon back ({release_click_type} click)...")
        print(f"[Auto Revive] DEBUG: About to perform {release_click_type} click at current position")
        print(f"[Auto Revive] DEBUG: Current mouse position before click: {pyautogui.position()}")
        
        if release_click_type.lower() == "right":
            print(f"[Auto Revive] DEBUG: Executing pyautogui.rightClick()")
            pyautogui.rightClick()
        else:
            print(f"[Auto Revive] DEBUG: Executing pyautogui.leftClick()")
            pyautogui.leftClick()
            
        print(f"[Auto Revive] DEBUG: Click executed, waiting {after_release_pokemon*1000}ms")
        time.sleep(after_release_pokemon)  # Wait after releasing pokemon
        
        print(f"[Auto Revive] Waiting additional 0.5s to ensure pokemon is released...")
        time.sleep(0.5)  # Extra wait to ensure the pokemon is properly released
        
        # STEP 5: Move back to original position
        print(f"[Auto Revive] Step 5: Returning to original position ({current_x}, {current_y})...")
        pyautogui.moveTo(current_x, current_y, duration=0.1)  # Quick smooth movement back
        
        total_time = (after_move + after_remove_pokemon + after_use_revive + after_release_pokemon) * 1000
        print(f"[Auto Revive] Process completed successfully! Total time: {total_time:.0f}ms")
        return True
        
    except Exception as e:
        print(f"[Auto Revive] ERROR: Process failed - {str(e)}")
        return False


def reset_all_todos():
    """Reset all todos to uncompleted state"""
    try:
        todo_config = load_from_file('todoConfig.json')
        
        def reset_todos_recursive(todos):
            for todo in todos:
                todo["completed"] = False
                if todo.get("children"):
                    reset_todos_recursive(todo["children"])
        
        reset_todos_recursive(todo_config["todos"])
        
        # Update the last reset timestamp
        todo_config["lastReset"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        save_to_file(todo_config, 'todoConfig.json')
        print("All todos have been reset")
        return {"success": True, "message": "All todos reset successfully"}
        
    except Exception as e:
        print(f"Error resetting todos: {str(e)}")
        return {"success": False, "message": f"Error resetting todos: {str(e)}"}


def get_todo_stats():
    """Get statistics about todos including last reset time"""
    try:
        todo_config = load_from_file('todoConfig.json')
        
        def count_todos(todos):
            total = 0
            completed = 0
            for todo in todos:
                total += 1
                if todo["completed"]:
                    completed += 1
                if todo.get("children"):
                    child_total, child_completed = count_todos(todo["children"])
                    total += child_total
                    completed += child_completed
            return total, completed
        
        total_count, completed_count = count_todos(todo_config["todos"])
        last_reset = todo_config.get("lastReset", "Never")
        
        return {
            "success": True,
            "stats": {
                "total": total_count,
                "completed": completed_count,
                "lastReset": last_reset
            }
        }
        
    except Exception as e:
        print(f"Error getting todo stats: {str(e)}")
        return {"success": False, "message": f"Error getting todo stats: {str(e)}"}


def add_todo_item(text, parent_id=None):
    """Add a new todo item to the list"""
    import uuid
    try:
        todo_config = load_from_file('todoConfig.json')
        
        # Generate a unique ID
        new_id = str(uuid.uuid4())
        
        new_todo = {
            "id": new_id,
            "text": text,
            "completed": False,
            "children": []
        }
        
        if parent_id:
            # Add as a child to the specified parent
            def add_to_parent(todos):
                for todo in todos:
                    if todo["id"] == parent_id:
                        todo["children"].append(new_todo)
                        return True
                    elif todo.get("children"):
                        if add_to_parent(todo["children"]):
                            return True
                return False
            
            if add_to_parent(todo_config["todos"]):
                save_to_file(todo_config, 'todoConfig.json')
                return {"success": True, "message": "Child todo added successfully", "todo": new_todo}
            else:
                return {"success": False, "message": "Parent todo not found"}
        else:
            # Add as a root level todo
            todo_config["todos"].append(new_todo)
            save_to_file(todo_config, 'todoConfig.json')
            return {"success": True, "message": "Todo added successfully", "todo": new_todo}
            
    except Exception as e:
        print(f"Error adding todo: {str(e)}")
        return {"success": False, "message": f"Error adding todo: {str(e)}"}


def toggle_todo_item(todo_id):
    """Toggle the completed status of a todo item and handle parent/child logic"""
    try:
        todo_config = load_from_file('todoConfig.json')
        
        def find_and_toggle(todos, target_id):
            for todo in todos:
                if todo["id"] == target_id:
                    # Toggle the todo
                    todo["completed"] = not todo["completed"]
                    
                    # If completing this todo, check all children
                    if todo["completed"] and todo.get("children"):
                        for child in todo["children"]:
                            child["completed"] = True
                            # Recursively mark children's children as completed
                            if child.get("children"):
                                mark_children_completed(child["children"])
                    
                    # If uncompleting this todo, uncheck all children
                    elif not todo["completed"] and todo.get("children"):
                        for child in todo["children"]:
                            child["completed"] = False
                            # Recursively mark children's children as uncompleted
                            if child.get("children"):
                                mark_children_uncompleted(child["children"])
                    
                    return todo
                elif todo.get("children"):
                    result = find_and_toggle(todo["children"], target_id)
                    if result:
                        # Check if all children are completed to auto-complete parent
                        if all(child["completed"] for child in todo["children"]):
                            todo["completed"] = True
                        else:
                            todo["completed"] = False
                        return result
            return None
        
        def mark_children_completed(children):
            for child in children:
                child["completed"] = True
                if child.get("children"):
                    mark_children_completed(child["children"])
        
        def mark_children_uncompleted(children):
            for child in children:
                child["completed"] = False
                if child.get("children"):
                    mark_children_uncompleted(child["children"])
        
        toggled_todo = find_and_toggle(todo_config["todos"], todo_id)
        
        if toggled_todo:
            save_to_file(todo_config, 'todoConfig.json')
            return {"success": True, "message": "Todo toggled successfully", "todo": toggled_todo}
        else:
            return {"success": False, "message": "Todo not found"}
            
    except Exception as e:
        print(f"Error toggling todo: {str(e)}")
        return {"success": False, "message": f"Error toggling todo: {str(e)}"}


def delete_todo_item(todo_id):
    """Delete a todo item from the list"""
    try:
        todo_config = load_from_file('todoConfig.json')
        
        def delete_from_todos(todos, target_id):
            for i, todo in enumerate(todos):
                if todo["id"] == target_id:
                    deleted_todo = todos.pop(i)
                    return deleted_todo
                elif todo.get("children"):
                    result = delete_from_todos(todo["children"], target_id)
                    if result:
                        return result
            return None
        
        deleted_todo = delete_from_todos(todo_config["todos"], todo_id)
        
        if deleted_todo:
            save_to_file(todo_config, 'todoConfig.json')
            return {"success": True, "message": "Todo deleted successfully", "todo": deleted_todo}
        else:
            return {"success": False, "message": "Todo not found"}
            
    except Exception as e:
        print(f"Error deleting todo: {str(e)}")
        return {"success": False, "message": f"Error deleting todo: {str(e)}"}


def update_todo_item(todo_id, new_text):
    """Update the text of a todo item"""
    try:
        todo_config = load_from_file('todoConfig.json')
        
        def find_and_update(todos, target_id, text):
            for todo in todos:
                if todo["id"] == target_id:
                    todo["text"] = text
                    return todo
                elif todo.get("children"):
                    result = find_and_update(todo["children"], target_id, text)
                    if result:
                        return result
            return None
        
        updated_todo = find_and_update(todo_config["todos"], todo_id, new_text)
        
        if updated_todo:
            save_to_file(todo_config, 'todoConfig.json')
            return {"success": True, "message": "Todo updated successfully", "todo": updated_todo}
        else:
            return {"success": False, "message": "Todo not found"}
            
    except Exception as e:
        print(f"Error updating todo: {str(e)}")
        return {"success": False, "message": f"Error updating todo: {str(e)}"}


# Weekly Todo Functions
def add_weekly_todo_item(text, parent_id=None):
    """Add a new weekly todo item to the list"""
    import uuid
    try:
        todo_config = load_from_file('weeklyTodoConfig.json')
        
        # Generate a unique ID
        new_id = str(uuid.uuid4())
        
        new_todo = {
            "id": new_id,
            "text": text,
            "completed": False,
            "children": []
        }
        
        if parent_id:
            # Add as a child to the specified parent
            def add_to_parent(todos):
                for todo in todos:
                    if todo["id"] == parent_id:
                        todo["children"].append(new_todo)
                        return True
                    elif todo.get("children"):
                        if add_to_parent(todo["children"]):
                            return True
                return False
            
            if add_to_parent(todo_config["todos"]):
                save_to_file(todo_config, 'weeklyTodoConfig.json')
                return {"success": True, "message": "Child weekly todo added successfully", "todo": new_todo}
            else:
                return {"success": False, "message": "Parent weekly todo not found"}
        else:
            # Add as a root level todo
            todo_config["todos"].append(new_todo)
            save_to_file(todo_config, 'weeklyTodoConfig.json')
            return {"success": True, "message": "Weekly todo added successfully", "todo": new_todo}
            
    except Exception as e:
        print(f"Error adding weekly todo: {str(e)}")
        return {"success": False, "message": f"Error adding weekly todo: {str(e)}"}


def toggle_weekly_todo_item(todo_id):
    """Toggle the completed status of a weekly todo item and handle parent/child logic"""
    try:
        todo_config = load_from_file('weeklyTodoConfig.json')
        
        def find_and_toggle(todos, target_id):
            for todo in todos:
                if todo["id"] == target_id:
                    # Toggle the todo
                    todo["completed"] = not todo["completed"]
                    
                    # If completing this todo, check all children
                    if todo["completed"] and todo.get("children"):
                        for child in todo["children"]:
                            child["completed"] = True
                            # Recursively mark children's children as completed
                            if child.get("children"):
                                mark_children_completed(child["children"])
                    
                    # If uncompleting this todo, uncheck all children
                    elif not todo["completed"] and todo.get("children"):
                        for child in todo["children"]:
                            child["completed"] = False
                            # Recursively mark children's children as uncompleted
                            if child.get("children"):
                                mark_children_uncompleted(child["children"])
                    
                    return todo
                elif todo.get("children"):
                    result = find_and_toggle(todo["children"], target_id)
                    if result:
                        # Check if all children are completed to auto-complete parent
                        if all(child["completed"] for child in todo["children"]):
                            todo["completed"] = True
                        else:
                            todo["completed"] = False
                        return result
            return None
        
        def mark_children_completed(children):
            for child in children:
                child["completed"] = True
                if child.get("children"):
                    mark_children_completed(child["children"])
        
        def mark_children_uncompleted(children):
            for child in children:
                child["completed"] = False
                if child.get("children"):
                    mark_children_uncompleted(child["children"])
        
        toggled_todo = find_and_toggle(todo_config["todos"], todo_id)
        
        if toggled_todo:
            save_to_file(todo_config, 'weeklyTodoConfig.json')
            return {"success": True, "message": "Weekly todo toggled successfully", "todo": toggled_todo}
        else:
            return {"success": False, "message": "Weekly todo not found"}
            
    except Exception as e:
        print(f"Error toggling weekly todo: {str(e)}")
        return {"success": False, "message": f"Error toggling weekly todo: {str(e)}"}


def delete_weekly_todo_item(todo_id):
    """Delete a weekly todo item from the list"""
    try:
        todo_config = load_from_file('weeklyTodoConfig.json')
        
        def delete_from_todos(todos, target_id):
            for i, todo in enumerate(todos):
                if todo["id"] == target_id:
                    deleted_todo = todos.pop(i)
                    return deleted_todo
                elif todo.get("children"):
                    result = delete_from_todos(todo["children"], target_id)
                    if result:
                        return result
            return None
        
        deleted_todo = delete_from_todos(todo_config["todos"], todo_id)
        
        if deleted_todo:
            save_to_file(todo_config, 'weeklyTodoConfig.json')
            return {"success": True, "message": "Weekly todo deleted successfully", "todo": deleted_todo}
        else:
            return {"success": False, "message": "Weekly todo not found"}
            
    except Exception as e:
        print(f"Error deleting weekly todo: {str(e)}")
        return {"success": False, "message": f"Error deleting weekly todo: {str(e)}"}


def update_weekly_todo_item(todo_id, new_text):
    """Update the text of a weekly todo item"""
    try:
        todo_config = load_from_file('weeklyTodoConfig.json')
        
        def find_and_update(todos, target_id, text):
            for todo in todos:
                if todo["id"] == target_id:
                    todo["text"] = text
                    return todo
                elif todo.get("children"):
                    result = find_and_update(todo["children"], target_id, text)
                    if result:
                        return result
            return None
        
        updated_todo = find_and_update(todo_config["todos"], todo_id, new_text)
        
        if updated_todo:
            save_to_file(todo_config, 'weeklyTodoConfig.json')
            return {"success": True, "message": "Weekly todo updated successfully", "todo": updated_todo}
        else:
            return {"success": False, "message": "Weekly todo not found"}
            
    except Exception as e:
        print(f"Error updating weekly todo: {str(e)}")
        return {"success": False, "message": f"Error updating weekly todo: {str(e)}"}


def reset_all_weekly_todos():
    """Reset all weekly todos to uncompleted state"""
    try:
        todo_config = load_from_file('weeklyTodoConfig.json')
        
        def reset_todos_recursive(todos):
            for todo in todos:
                todo["completed"] = False
                if todo.get("children"):
                    reset_todos_recursive(todo["children"])
        
        reset_todos_recursive(todo_config["todos"])
        
        # Update the last reset timestamp
        todo_config["lastReset"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        save_to_file(todo_config, 'weeklyTodoConfig.json')
        print("All weekly todos have been reset")
        return {"success": True, "message": "All weekly todos reset successfully"}
        
    except Exception as e:
        print(f"Error resetting weekly todos: {str(e)}")
        return {"success": False, "message": f"Error resetting weekly todos: {str(e)}"}


def get_weekly_todo_stats():
    """Get statistics about weekly todos including last reset time"""
    try:
        todo_config = load_from_file('weeklyTodoConfig.json')
        
        def count_todos(todos):
            total = 0
            completed = 0
            for todo in todos:
                total += 1
                if todo["completed"]:
                    completed += 1
                if todo.get("children"):
                    child_total, child_completed = count_todos(todo["children"])
                    total += child_total
                    completed += child_completed
            return total, completed
        
        total_count, completed_count = count_todos(todo_config["todos"])
        last_reset = todo_config.get("lastReset", "Never")
        
        return {
            "success": True,
            "stats": {
                "total": total_count,
                "completed": completed_count,
                "lastReset": last_reset
            }
        }
        
    except Exception as e:
        print(f"Error getting weekly todo stats: {str(e)}")
        return {"success": False, "message": f"Error getting weekly todo stats: {str(e)}"}
