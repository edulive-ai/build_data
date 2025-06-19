# modules/gallery_manager.py
import os
import time
import re
from pathlib import Path

class GalleryManager:
    def __init__(self):
        self.books_detections_dir = "books_detections"
        self.books_cropped_dir = "books_cropped"
    
    def get_available_books(self):
        """
        Lấy danh sách các sách có sẵn cho Gallery
        Chỉ scan trong books_detections và books_cropped
        """
        books = set()
        
        # Scan books_detections
        if os.path.exists(self.books_detections_dir):
            try:
                for item in os.listdir(self.books_detections_dir):
                    item_path = os.path.join(self.books_detections_dir, item)
                    if os.path.isdir(item_path):
                        books.add(item)
            except Exception as e:
                print(f"Error scanning {self.books_detections_dir}: {e}")
        
        # Scan books_cropped
        if os.path.exists(self.books_cropped_dir):
            try:
                for item in os.listdir(self.books_cropped_dir):
                    item_path = os.path.join(self.books_cropped_dir, item)
                    if os.path.isdir(item_path):
                        books.add(item)
            except Exception as e:
                print(f"Error scanning {self.books_cropped_dir}: {e}")
        
        return sorted(list(books))
    
    def get_detection_images(self, book_name):
        """
        Lấy danh sách ảnh detection cho một sách
        
        Args:
            book_name (str): Tên sách (ví dụ: "30-de-thi")
            
        Returns:
            dict: {'success': bool, 'images': list, 'error': str}
        """
        try:
            if not book_name:
                return {'success': False, 'error': 'Thiếu tên sách'}
            
            detection_dir = os.path.join(self.books_detections_dir, book_name)
            images = []
            
            if not os.path.exists(detection_dir):
                return {'success': True, 'images': [], 'message': f'Thư mục {detection_dir} không tồn tại'}
            
            # Lấy tất cả file ảnh trong thư mục
            for file in sorted(os.listdir(detection_dir)):
                if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    file_path = os.path.join(detection_dir, file)
                    
                    try:
                        file_stat = os.stat(file_path)
                        
                        images.append({
                            'name': file,
                            'url': f"/detection_images/{book_name}/{file}",
                            'path': file_path,
                            'size': f"{file_stat.st_size / 1024:.1f} KB",
                            'date': time.strftime('%Y-%m-%d %H:%M', time.localtime(file_stat.st_mtime))
                        })
                    except Exception as e:
                        print(f"Error processing file {file}: {e}")
                        continue
            
            return {'success': True, 'images': images}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_cropped_images(self, book_name):
        """
        Lấy danh sách ảnh crop cho một sách
        
        Args:
            book_name (str): Tên sách (ví dụ: "30-de-thi")
            
        Returns:
            dict: {'success': bool, 'images': list, 'error': str}
        """
        try:
            if not book_name:
                return {'success': False, 'error': 'Thiếu tên sách'}
            
            cropped_dir = os.path.join(self.books_cropped_dir, book_name)
            images = []
            
            if not os.path.exists(cropped_dir):
                return {'success': True, 'images': [], 'message': f'Thư mục {cropped_dir} không tồn tại'}
            
            # Duyệt qua các thư mục image_xxxx
            for folder in sorted(os.listdir(cropped_dir)):
                folder_path = os.path.join(cropped_dir, folder)
                
                if os.path.isdir(folder_path) and folder.startswith('image_'):
                    # Duyệt qua các file ảnh trong thư mục
                    for file in sorted(os.listdir(folder_path)):
                        if file.lower().endswith('.png'):
                            file_path = os.path.join(folder_path, file)
                            
                            try:
                                file_stat = os.stat(file_path)
                                
                                # Extract class từ tên file (crop_xxx_clsN.png)
                                class_match = re.search(r'cls(\d+)', file)
                                class_id = int(class_match.group(1)) if class_match else None
                                
                                images.append({
                                    'name': file,
                                    'folder': folder,
                                    'url': f"/images/{self.books_cropped_dir}/{book_name}/{folder}/{file}",
                                    'path': file_path,
                                    'size': f"{file_stat.st_size / 1024:.1f} KB",
                                    'date': time.strftime('%Y-%m-%d %H:%M', time.localtime(file_stat.st_mtime)),
                                    'class': class_id
                                })
                            except Exception as e:
                                print(f"Error processing file {file}: {e}")
                                continue
            
            return {'success': True, 'images': images}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_book_info(self, book_name):
        """
        Lấy thông tin tổng quan về một sách
        
        Args:
            book_name (str): Tên sách
            
        Returns:
            dict: Thông tin về sách
        """
        try:
            detection_dir = os.path.join(self.books_detections_dir, book_name)
            cropped_dir = os.path.join(self.books_cropped_dir, book_name)
            
            info = {
                'name': book_name,
                'has_detection': os.path.exists(detection_dir),
                'has_cropped': os.path.exists(cropped_dir),
                'detection_count': 0,
                'cropped_count': 0,
                'folders_count': 0
            }
            
            # Đếm ảnh detection
            if info['has_detection']:
                try:
                    detection_files = [f for f in os.listdir(detection_dir) 
                                     if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                    info['detection_count'] = len(detection_files)
                except:
                    pass
            
            # Đếm ảnh crop và folder
            if info['has_cropped']:
                try:
                    folders = [f for f in os.listdir(cropped_dir) 
                             if os.path.isdir(os.path.join(cropped_dir, f)) and f.startswith('image_')]
                    info['folders_count'] = len(folders)
                    
                    # Đếm tổng số ảnh crop
                    total_cropped = 0
                    for folder in folders:
                        folder_path = os.path.join(cropped_dir, folder)
                        try:
                            cropped_files = [f for f in os.listdir(folder_path) 
                                           if f.lower().endswith('.png')]
                            total_cropped += len(cropped_files)
                        except:
                            continue
                    info['cropped_count'] = total_cropped
                except:
                    pass
            
            return info
            
        except Exception as e:
            return {'error': str(e)}
    
    def validate_book_exists(self, book_name):
        """
        Kiểm tra xem sách có tồn tại không
        
        Args:
            book_name (str): Tên sách
            
        Returns:
            dict: {'exists': bool, 'has_detection': bool, 'has_cropped': bool}
        """
        detection_dir = os.path.join(self.books_detections_dir, book_name)
        cropped_dir = os.path.join(self.books_cropped_dir, book_name)
        
        has_detection = os.path.exists(detection_dir)
        has_cropped = os.path.exists(cropped_dir)
        
        return {
            'exists': has_detection or has_cropped,
            'has_detection': has_detection,
            'has_cropped': has_cropped
        }
    
    def get_debug_info(self):
        """
        Lấy thông tin debug về thư mục Gallery
        
        Returns:
            dict: Thông tin debug chi tiết
        """
        debug_info = {
            'current_directory': os.getcwd(),
            'books_detections_dir': self.books_detections_dir,
            'books_cropped_dir': self.books_cropped_dir,
            'books_detections_exists': os.path.exists(self.books_detections_dir),
            'books_cropped_exists': os.path.exists(self.books_cropped_dir),
            'available_books': self.get_available_books()
        }
        
        # Chi tiết thư mục books_detections
        if debug_info['books_detections_exists']:
            try:
                debug_info['books_detections_contents'] = [
                    {
                        'name': item,
                        'is_dir': os.path.isdir(os.path.join(self.books_detections_dir, item)),
                        'path': os.path.join(self.books_detections_dir, item)
                    }
                    for item in os.listdir(self.books_detections_dir)
                ]
            except Exception as e:
                debug_info['books_detections_error'] = str(e)
        
        # Chi tiết thư mục books_cropped
        if debug_info['books_cropped_exists']:
            try:
                debug_info['books_cropped_contents'] = [
                    {
                        'name': item,
                        'is_dir': os.path.isdir(os.path.join(self.books_cropped_dir, item)),
                        'path': os.path.join(self.books_cropped_dir, item)
                    }
                    for item in os.listdir(self.books_cropped_dir)
                ]
            except Exception as e:
                debug_info['books_cropped_error'] = str(e)
        
        return debug_info