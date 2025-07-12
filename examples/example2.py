from pycomfy import ComfyAPI, WorkflowError, MissingModelError
import sys

# --- Exemple 2 : La voie experte pour un contrôle total ---
# Idéal pour les workflows complexes et personnalisés.

# Optionnel : Fournissez le chemin vers votre dossier ComfyUI pour activer le téléchargement automatique.
COMFYUI_PATH = None 

try:
    # 1. Initialisez l'API. Le chemin comfyui_path est aussi utilisable ici.
    api = ComfyAPI("127.0.0.1:8188", comfyui_path=COMFYUI_PATH)
    workflow = api.load_workflow("my_workflow_api.json") 
    print("Workflow personnalisé chargé.")

    # 2. Utilisez les outils d'inspection et de modification pour configurer le workflow
    
    # Modifier le Checkpoint (si le modèle est manquant, l'erreur vous le signalera)
    ckpt_loaders = workflow.get_nodes_by_class("CheckpointLoaderSimple")
    if ckpt_loaders:
        workflow.set_node(ckpt_loaders[0], {"ckpt_name": "v1-5-pruned-emaonly-fp16.safetensors"})
        print("Modèle de checkpoint configuré.")

    # Modifier le Sampler
    samplers = workflow.get_nodes_by_class("KSampler")
    if samplers:
        workflow.set_node(samplers[0], {"steps": 15, "cfg": 7.0})
        print("Paramètres du sampler principal configurés.")
    
    # 3. Exécutez le workflow en utilisant les raccourcis de base pour les prompts et la seed
    print("\nLancement de l'exécution du workflow expert...")
    images = workflow.execute(
        positive_prompt="a robot programmer coding at a desk, synthwave, futuristic",
        negative_prompt="bad hands, text, watermark",
        seed=999
    )

    if images:
        images[0].save("robot_programmer_expert.png")
        print("\nImage 'robot_programmer_expert.png' sauvegardée !")
    else:
        print("\nLa génération d'image a échoué.")

except FileNotFoundError:
    print("Erreur: Le fichier 'my_workflow_api.json' est introuvable.")
except MissingModelError as e:
    print(f"\n--- ERREUR : MODÈLE MANQUANT OU ACTION REQUISE ---\n{e}")
except Exception as e:
    print(f"\nUne erreur inattendue est survenue: {e}")