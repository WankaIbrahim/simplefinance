import requests
USE_LOCAL = False

if USE_LOCAL:
    BASE_URL = "http://localhost:7071"
else:
    BASE_URL = "https://iaw1e22-quiplash.azurewebsites.net"
player_register_url = f"{BASE_URL}/player/register?code=q_oTBPnwhyU3raS7hh5YEZ7SR_HI8gy2eFy-G1mAB5NEAzFu2NW8Mg=="
player_login_url = f"{BASE_URL}/player/login?code=9q4O-id3tGJTjwwuieilRCvaxApHkafNZC0MUtxwDnQXAzFu_AKtOQ=="
player_update_url = f"{BASE_URL}/player/update?code=Y_6SS1jkbK5zdkEgghlljoqqvLLDkzTFGJguSm65_5o9AzFu1QMZlw=="
prompt_create_url = f"{BASE_URL}/prompt/create?code=nvt3r7I5_jlSewhv7gy8s68-AC6JwZtIMdgRCRhA1CQ5AzFuMbarqA=="
prompt_moderate_url = f"{BASE_URL}/prompt/moderate?code=uytBFS3N7qfQbppi9spRh2w5wqm6xThDPwoIln0DYAifAzFuUgi5Uw=="
prompt_delete_url = f"{BASE_URL}/prompt/delete?code=SJh23TdDu9jjSCQ_klRd1HLzQ7yxSk9WyDrBxlfjHzA_AzFuoBncTA=="
utils_get_url = f"{BASE_URL}/utils/get?code=hsM_3PCIxPMyR-EWH_AIRJEVjDiYiNcDpHijQjxR1jxOAzFuXi5GuA=="

player_register_input = {"username":  "Ibrahim2" , "password" : "@iaw1e22"}
player_login_input = {"username":  "Richard" , "password" : "candyfloss"}
player_update_input = {"username": "Richard" , "add_to_games_played": 3 , "add_to_score" : 10 }
prompt_create_input = {"text": "2 Polish food is super-duper buns", "username": "Ilika", "tags" : ["Apples"] }
prompt_moderate_input = {"prompt-ids": ["96de51f4-6cdf-41d4-82c6-8b33b27d67eb","cf5f13aa-801e-435e-897c-a75a1a1a2d35"] }
prompt_delete_input = {"player" : "Richard" }
utils_get_input = {"players":  ["Richard"], "tag_list": ["Computer"]}

#player_register_response = requests.post(player_register_url, json=player_register_input)
#player_login_response = requests.get(player_login_url, json=player_login_input)
#player_update_response = requests.put(player_update_url, json=player_update_input)
#prompt_create_response = requests.post(prompt_create_url, json=prompt_create_input)
promp_moderate_response = requests.post(prompt_moderate_url, json=prompt_moderate_input)
#prompt_delete_response = requests.post(prompt_delete_url, json=prompt_delete_input)
#utils_get_response = requests.get(utils_get_url, json=utils_get_input)

#print("Player Register Response:", player_register_response.status_code, player_register_response.text)
#print("Player Login Response:", player_login_response.status_code, player_login_response.text)
#print("Player Update Response:", player_update_response.status_code, player_update_response.text)
#print("Prompt Create Response:", prompt_create_response.status_code, prompt_create_response.text)
print("Prompt Moderate Response:", promp_moderate_response.status_code, promp_moderate_response.text)
#print("Prompt Delete Response:", prompt_delete_response.status_code, prompt_delete_response.text)
#print("Print Utils Get Response:", utils_get_response.status_code, utils_get_response.text)
