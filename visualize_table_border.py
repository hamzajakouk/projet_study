import fitz  # PyMuPDF
import json
from pathlib import Path

def save_pdf_with_bbox(pdf_path, page_num=1, output_path=None):
    """
    Sauvegarde un PDF avec la bounding box dessinée dessus
    
    Args:
        pdf_path (str): Chemin vers le PDF original
        page_num (int): Numéro de page
        output_path (str): Chemin de sortie (optionnel)
    
    Returns:
        str: Chemin du PDF sauvegardé
    """
    bbox_coords = {
        "l": 27.998722076416016,
        "t": 374.07794189453125,
        "r": 577.8319091796875,
        "b": 204.11077880859375,
        "coord_origin": "BOTTOMLEFT"
    }
    
    try:
        # Ouvrir le PDF
        doc = fitz.open(pdf_path)
        page = doc[page_num-1]  # PyMuPDF utilise index 0
        
        # Obtenir les dimensions de la page
        page_rect = page.rect
        page_width = page_rect.width
        page_height = page_rect.height
        
        print(f"📄 Dimensions page: {page_width:.1f} x {page_height:.1f} points")
        
        # Convertir les coordonnées
        x0 = bbox_coords["l"]
        y0 = page_height - bbox_coords["t"]  # Flip Y
        x1 = bbox_coords["r"]
        y1 = page_height - bbox_coords["b"]  # Flip Y
        
        # Créer le rectangle
        bbox_rect = fitz.Rect(x0, y0, x1, y1)
        
        # Dessiner le rectangle sur la page
        page.draw_rect(bbox_rect, color=(1, 0, 0), width=3, fill=None)  # Rouge, sans remplissage
        
        # Ajouter du texte pour identifier la bbox
        text_point = fitz.Point(x0 + 5, y0 - 5)
        page.insert_text(text_point, "Table BBox", fontsize=12, color=(1, 0, 0))
        
        print(f"🎯 Rectangle rouge ajouté aux coordonnées: ({x0:.1f}, {y0:.1f}) à ({x1:.1f}, {y1:.1f})")
        
        # Définir le chemin de sortie
        if output_path is None:
            pdf_stem = Path(pdf_path).stem
            output_path = f"{pdf_stem}_with_bbox.pdf"
        
        # Sauvegarder le PDF modifié
        doc.save(output_path)
        doc.close()
        
        print(f"💾 PDF sauvegardé avec bbox: {output_path}")
        
        return output_path
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None

def save_pdf_with_multiple_bboxes(pdf_path, bboxes_list, output_path=None):
    """
    Sauvegarde un PDF avec plusieurs bounding boxes
    
    Args:
        pdf_path (str): Chemin vers le PDF original
        bboxes_list (list): Liste des bboxes avec leurs pages
        output_path (str): Chemin de sortie
    
    Returns:
        str: Chemin du PDF sauvegardé
    """
    
    try:
        # Ouvrir le PDF
        doc = fitz.open(pdf_path)
        
        # Couleurs pour différentes tables
        colors = [(1, 0, 0), (0, 0, 1), (0, 1, 0), (1, 0.5, 0), (1, 0, 1), (0.5, 0.5, 0.5)]
        
        # Grouper les bboxes par page
        pages_bboxes = {}
        for bbox_info in bboxes_list:
            page_no = bbox_info.get("page_no", 1)
            if page_no not in pages_bboxes:
                pages_bboxes[page_no] = []
            pages_bboxes[page_no].append(bbox_info)
        
        # Traiter chaque page
        for page_no, page_bboxes in pages_bboxes.items():
            if page_no <= len(doc):
                page = doc[page_no - 1]  # Index 0
                page_height = page.rect.height
                
                print(f"📄 Page {page_no}: {len(page_bboxes)} table(s)")
                
                # Dessiner chaque bbox sur cette page
                for idx, bbox_info in enumerate(page_bboxes):
                    bbox_coords = bbox_info["bbox"]
                    table_idx = bbox_info.get("table_idx", idx)
                    color = colors[idx % len(colors)]
                    
                    # Convertir les coordonnées
                    x0 = bbox_coords["l"]
                    y0 = page_height - bbox_coords["t"]
                    x1 = bbox_coords["r"]
                    y1 = page_height - bbox_coords["b"]
                    
                    # Créer et dessiner le rectangle
                    bbox_rect = fitz.Rect(x0, y0, x1, y1)
                    page.draw_rect(bbox_rect, color=color, width=3, fill=None)
                    
                    # Ajouter le label
                    text_point = fitz.Point(x0 + 5, y0 - 5)
                    page.insert_text(text_point, f"Table {table_idx}", fontsize=11, color=color)
                    
                    print(f"   🎯 Table {table_idx}: ({x0:.1f}, {y0:.1f}) à ({x1:.1f}, {y1:.1f})")
        
        # Définir le chemin de sortie
        if output_path is None:
            pdf_stem = Path(pdf_path).stem
            output_path = f"{pdf_stem}_with_tables_bbox.pdf"
        
        # Sauvegarder le PDF modifié
        doc.save(output_path)
        doc.close()
        
        print(f"💾 PDF sauvegardé avec {len(bboxes_list)} table(s): {output_path}")
        
        return output_path
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None

def extract_table_bboxes_from_json(json_path):
    """
    Extrait les bounding boxes des tables depuis le fichier JSON
    """
    print(f"📖 Lecture du fichier JSON: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    table_bboxes = []
    
    if "tables" in data:
        for idx, table in enumerate(data["tables"]):
            if "prov" in table and len(table["prov"]) > 0:
                for prov in table["prov"]:
                    bbox_info = {
                        "table_idx": idx,
                        "page_no": prov.get("page_no", 1),
                        "bbox": prov.get("bbox", {}),
                        "coord_origin": prov["bbox"].get("coord_origin", "BOTTOMLEFT") if "bbox" in prov else "BOTTOMLEFT"
                    }
                    table_bboxes.append(bbox_info)
                    
                    print(f"  📊 Table {idx}: Page {bbox_info['page_no']}, "
                          f"BBox: L={bbox_info['bbox'].get('l', 0):.1f}, "
                          f"T={bbox_info['bbox'].get('t', 0):.1f}, "
                          f"R={bbox_info['bbox'].get('r', 0):.1f}, "
                          f"B={bbox_info['bbox'].get('b', 0):.1f}")
    
    print(f"✅ Trouvé {len(table_bboxes)} tables avec bounding boxes")
    return table_bboxes

def save_pdf_from_json(pdf_path, json_path, output_path=None):
    """
    Sauvegarde un PDF avec toutes les tables du JSON
    
    Args:
        pdf_path (str): Chemin vers le PDF original
        json_path (str): Chemin vers le fichier JSON
        output_path (str): Chemin de sortie (optionnel)
    
    Returns:
        str: Chemin du PDF sauvegardé
    """
    
    # Extraire les bboxes du JSON
    table_bboxes = extract_table_bboxes_from_json(json_path)
    
    if not table_bboxes:
        print("❌ Aucune table trouvée dans le JSON")
        return None
    
    # Sauvegarder le PDF avec toutes les bboxes
    return save_pdf_with_multiple_bboxes(pdf_path, table_bboxes, output_path)

def process_all_files_to_pdf(pdf_dir="raws_split", json_dir="json_extracted", output_dir="pdfs_with_bbox"):
    """
    Traite tous les fichiers et génère des PDFs avec bboxes
    
    Args:
        pdf_dir (str): Répertoire des PDFs originaux
        json_dir (str): Répertoire des JSONs
        output_dir (str): Répertoire de sortie
    """
    
    # Créer le répertoire de sortie
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    pdf_path = Path(pdf_dir)
    json_path = Path(json_dir)
    
    # Lister tous les fichiers JSON
    json_files = [f for f in json_path.glob("*.json") if "summary" not in f.name]
    
    print(f"🔍 Trouvé {len(json_files)} fichiers à traiter")
    
    results = []
    
    for json_file in json_files:
        # Trouver le PDF correspondant
        pdf_name = json_file.stem + ".pdf"
        pdf_file = pdf_path / pdf_name
        
        if pdf_file.exists():
            print(f"\n{'='*60}")
            print(f"📄 Traitement: {pdf_name}")
            
            # Définir le nom de sortie
            output_name = f"{json_file.stem}_with_tables.pdf"
            output_file = output_path / output_name
            
            # Traiter le fichier
            result = save_pdf_from_json(str(pdf_file), str(json_file), str(output_file))
            
            if result:
                results.append({
                    "original": str(pdf_file),
                    "output": str(result),
                    "status": "success"
                })
                print(f"✅ Succès: {result}")
            else:
                results.append({
                    "original": str(pdf_file),
                    "output": None,
                    "status": "error"
                })
                print(f"❌ Erreur lors du traitement")
        else:
            print(f"⚠️  PDF non trouvé: {pdf_file}")
    
    # Résumé
    success_count = len([r for r in results if r["status"] == "success"])
    print(f"\n🎉 Traitement terminé: {success_count}/{len(json_files)} fichiers réussis")
    print(f"📁 PDFs avec bboxes sauvegardés dans: {output_dir}/")
    
    return results

# Utilisation
if __name__ == "__main__":
    
    print("🚀 Génération de PDFs avec bounding boxes...")
    
    # Option 1: Un seul fichier avec bbox hardcodée
    print("\n📋 TEST 1: Bbox hardcodée")
    pdf_file = "raws_split/BNC_RG_2024Q1_part05.pdf"
    
    # Option 2: Un fichier avec tables JSON
    print("\n📋 TEST 2: Tables depuis JSON")
    json_file = "json_extracted/BNC_RG_2024Q1_part05.json"
    result2 = save_pdf_from_json(pdf_file, json_file, "test_tables_5.pdf")
    
    # Option 3: Traiter tous les fichiers
    print("\n📋 TEST 3: Batch processing")
    # process_all_files_to_pdf()
    
    print("\n🎉 Terminé ! Ouvrez les PDFs générés pour voir les bounding boxes.")