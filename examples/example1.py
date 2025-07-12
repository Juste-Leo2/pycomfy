from pycomfy import ComfyAPI, MissingModelError
import sys

# --- Exemple 1 : La voie simple et directe avec les nouvelles fonctions "Preset" ---

# Optionnel : Fournissez le chemin vers votre dossier ComfyUI pour activer le téléchargement automatique.
# Remplacez "C:/path/to/your/ComfyUI" par votre chemin réel.
COMFYUI_PATH = "C:/path/to/your/ComfyUI" # Ou None si vous ne voulez pas activer le téléchargement.

try:
    # 1. Initialisez l'API en fournissant le chemin vers ComfyUI
    # Si le chemin est None, le téléchargement automatique sera désactivé.
    api = ComfyAPI("127.0.0.1:8188", comfyui_path=COMFYUI_PATH)

    # 2. Appelez une des nouvelles fonctions "preset"
    # C'est beaucoup plus simple ! Pas besoin de spécifier le nom du checkpoint.
    print("Génération d'une image avec le preset FLUX Schnell...")
    images = api.text_to_image_flux_schnell(
        positive_prompt="a majestic lion on a throne, cinematic lighting, highly detailed",
        negative_prompt="blurry, cartoon, bad art",
        seed=42,
        # Vous pouvez toujours surcharger les paramètres du preset si besoin
        # steps=8 
    )
    
    # 3. Sauvegardez le résultat
    if images:
        images[0].save("lion_king_flux.png")
        print("\nImage 'lion_king_flux.png' sauvegardée !")
    else:
        print("\nLa génération d'image a échoué.")

except MissingModelError as e:
    # Cette erreur peut maintenant indiquer qu'un modèle a été téléchargé et qu'un redémarrage est nécessaire.
    print(f"\n--- ERREUR : MODÈLE MANQUANT OU ACTION REQUISE ---\n{e}")
except Exception as e:
    print(f"\nUne erreur inattendue est survenue: {e}")