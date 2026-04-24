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
    Fetches all images from a specific Cloudinary folder, sorted oldest to newest.
    Returns a list of image URLs.
    """
    init_cloudinary()
    
    try:
        # Search API to get resources in folder, sorted by created_at ascending (oldest first)
        response = cloudinary.api.resources(
            type="upload",
            prefix=folder_name + "/",
            max_results=500,
            direction="asc" # oldest to newest
        )
        
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

if __name__ == "__main__":
    # Test
    # print(get_images_from_folder("my_classic_cars"))
    pass
