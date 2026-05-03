import os
import cloudinary
import cloudinary.api

def init_cloudinary():
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME")
    api_key = os.environ.get("CLOUDINARY_API_KEY")
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
    
    if not all([cloud_name, api_key, api_secret]):
        raise ValueError("Cloudinary credentials are not fully set in environment variables.")

    cloudinary.config(
        cloud_name = cloud_name,
        api_key = api_key,
        api_secret = api_secret,
        secure = True
    )

def get_images_from_folder(folder_name):
    """
    Fetches all images from a specific Cloudinary folder using Search API.
    """
    init_cloudinary()
    import cloudinary.search
    
    try:
        # Search API is more robust for folder matching
        expression = f"folder:\"{folder_name}\" AND resource_type:image"
        
        response = cloudinary.search.Search() \
            .expression(expression) \
            .sort_by("created_at", "asc") \
            .max_results(500) \
            .execute()
        
        images = []
        for resource in response.get('resources', []):
            images.append({
                'public_id': resource['public_id'],
                'url': resource['secure_url'],
                'created_at': resource['created_at']
            })
            
        return images
    except Exception as e:
        print(f"Error fetching images from Cloudinary folder '{folder_name}': {e}")
        return []

def delete_image(public_id):
    """
    Deletes an image from Cloudinary permanently after posting.
    """
    init_cloudinary()
    import cloudinary.uploader
    try:
        result = cloudinary.uploader.destroy(public_id)
        print(f"Cloudinary deletion result for {public_id}: {result}")
    except Exception as e:
        print(f"Failed to delete image {public_id} from Cloudinary: {e}")

if __name__ == "__main__":
    # Test
    # print(get_images_from_folder("my_classic_cars"))
    pass
