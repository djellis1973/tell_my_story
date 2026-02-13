def search_all_answers(search_query):
    if not search_query or len(search_query) < 2: 
        return []
    
    results = []
    search_query = search_query.lower()
    
    for session in (st.session_state.current_question_bank or []):
        session_id = session["id"]
        session_data = st.session_state.responses.get(session_id, {})
        
        for question_text, answer_data in session_data.get("questions", {}).items():
            answer = answer_data.get("answer", "")
            has_images = answer_data.get("has_images", False)
            image_refs = answer_data.get("image_refs", [])
            
            # Search in answer text AND image captions AND image references
            if (search_query in answer.lower() or 
                search_query in question_text.lower() or
                any(search_query in ref.lower() for ref in image_refs) or
                (has_images and any(search_query in img.get("caption", "").lower() 
                                  for img in answer_data.get("images", [])))):
                
                image_captions = []
                if has_images and st.session_state.image_handler:
                    images = st.session_state.image_handler.get_images_for_answer(session_id, question_text)
                    image_captions = [img.get("caption", "") for img in images if img.get("caption")]
                
                results.append({
                    "session_id": session_id, 
                    "session_title": session["title"],
                    "question": question_text, 
                    "answer": answer[:300] + "..." if len(answer) > 300 else answer,
                    "timestamp": answer_data.get("timestamp", ""), 
                    "word_count": len(re.sub(r'\[Image:.*?\]', '', answer).split()),
                    "has_images": has_images, 
                    "image_count": answer_data.get("image_count", 0),
                    "image_captions": image_captions,
                    "image_refs": image_refs
                })
    
    results.sort(key=lambda x: x["timestamp"], reverse=True)
    return results
