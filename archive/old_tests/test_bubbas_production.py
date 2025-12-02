"""
Production test for Bubba's 33 menu scraping
Tests the full CloudDestroyer pipeline with database integration
"""

import json
import time
from datetime import datetime
from db_config import DatabaseManager

# Import the production API
from api import RestaurantMenuScraper

def test_bubbas_menu_scrape():
    """Test scraping Bubba's 33 menu and storing in database"""

    print("=" * 80)
    print("BUBBA'S 33 MENU SCRAPING TEST - PRODUCTION")
    print("=" * 80)
    print(f"Started: {datetime.now()}")
    print()

    # Initialize database manager
    db = DatabaseManager()

    # Test URL
    url = "https://www.bubbas33.com"
    restaurant_name = "Bubba's 33"

    print(f"Target: {url}")
    print(f"Restaurant: {restaurant_name}")
    print()

    # Step 1: Create scraping job in database
    print("Step 1: Creating scraping job in CloudDestroyer database...")
    try:
        job_id = db.create_job(
            job_type='menu_extraction',
            target_url=url,
            entity_type='restaurant',
            entity_id='bubbas33_test',
            priority=80
        )
        print(f"+ Job created: job_id={job_id}")
    except Exception as e:
        print(f"- Failed to create job: {e}")
        return

    print()

    # Step 2: Initialize scraper
    print("Step 2: Initializing RestaurantMenuScraper...")
    scraper = RestaurantMenuScraper()
    print("+ Scraper initialized (with CloudDestroyer bypass enabled)")
    print()

    # Step 3: Extract menu
    print("Step 3: Extracting menu (this may take 1-3 minutes)...")
    print("-" * 80)

    start_time = time.time()

    try:
        result = scraper.extract_menu(url)

        duration = time.time() - start_time

        print("-" * 80)
        print(f"+ Menu extraction completed in {duration:.2f} seconds")
        print()

        # Step 4: Display results
        print("Step 4: Extraction Results")
        print("-" * 80)

        # Handle Pydantic model
        if hasattr(result, 'model_dump'):
            result_dict = result.model_dump()
        elif hasattr(result, 'dict'):
            result_dict = result.dict()
        else:
            result_dict = result

        print(f"Success: {result_dict.get('success', False)}")
        print(f"Menu URL: {result_dict.get('menu_url', 'N/A')}")
        print(f"Site Type: {result_dict.get('site_type', 'N/A')}")
        print(f"Extraction Method: {result_dict.get('extraction_method', 'N/A')}")
        print(f"Confidence Score: {result_dict.get('confidence_score', 0)}")

        # Extract menu data (could be nested or top-level)
        menu_data = result_dict.get('menu_data', result_dict)
        categories = menu_data.get('categories', [])
        items = menu_data.get('items', [])

        # Handle categories as dict or list
        if isinstance(categories, dict):
            category_names = list(categories.keys())
            category_count = len(category_names)
        else:
            category_names = [cat.get('name', 'Unknown') for cat in categories]
            category_count = len(categories)

        print(f"\nCategories Found: {category_count}")
        for i, cat_name in enumerate(category_names[:5], 1):
            print(f"  {i}. {cat_name}")
        if category_count > 5:
            print(f"  ... and {category_count - 5} more")

        print(f"\nMenu Items Found: {len(items)}")

        # Count items with prices
        items_with_prices = sum(1 for item in items if item.get('price'))
        print(f"Items with Prices: {items_with_prices}")

        # Show sample items
        print("\nSample Menu Items:")
        for i, item in enumerate(items[:10], 1):
            name = item.get('name', 'Unknown')
            price = item.get('price', 'N/A')
            category = item.get('category', 'Uncategorized')
            print(f"  {i}. [{category}] {name} - ${price}" if price != 'N/A' else f"  {i}. [{category}] {name}")

        if len(items) > 10:
            print(f"  ... and {len(items) - 10} more items")

        print()

        # Step 5: Store results in database
        print("Step 5: Storing results in CloudDestroyer database...")

        try:
            # Prepare structured data
            structured_data = {
                'categories': categories,
                'items': items,
                'metadata': {
                    'extracted_at': datetime.now().isoformat(),
                    'site_type': result_dict.get('site_type'),
                    'extraction_method': result_dict.get('extraction_method'),
                    'menu_url': result_dict.get('menu_url')
                }
            }

            # Complete the job
            db.complete_job(
                job_id=job_id,
                status='completed',
                items_extracted=len(items),
                processing_time_seconds=duration,
                structured_data=json.dumps(structured_data),
                confidence_score=result_dict.get('confidence_score', 0.8),
                extraction_method=result_dict.get('extraction_method'),
                items_with_prices=items_with_prices,
                price_source='initial_scrape' if items_with_prices > 0 else None
            )

            print(f"+ Results stored successfully")
            print(f"  - Job ID: {job_id}")
            print(f"  - Status: completed")
            print(f"  - Items: {len(items)}")
            print(f"  - Categories: {len(categories)}")
            print(f"  - Items with prices: {items_with_prices}")

        except Exception as e:
            print(f"- Failed to store results: {e}")
            import traceback
            traceback.print_exc()

        print()

        # Step 6: Sync to FoodFinder (optional)
        print("Step 6: Syncing to FoodFinder database...")
        try:
            # First, upsert restaurant
            restaurant_id = f"bubbas33_{url.split('//')[-1].split('/')[0].replace('.', '_')}"

            cursor = db.foodfinder.cursor()
            cursor.execute(
                "EXEC sp_UpsertRestaurant @RestaurantId=?, @Name=?, @Website=?, @IsChain=1",
                restaurant_id, restaurant_name, url
            )
            db.foodfinder.commit()

            print(f"+ Restaurant record created/updated: {restaurant_id}")

            # Import menu data
            menu_json = json.dumps(structured_data)

            cursor = db.foodfinder.cursor()
            cursor.execute(
                "EXEC sp_ImportMenuData @RestaurantId=?, @MenuData=?, @MenuSource='clouddestroyer'",
                restaurant_id, menu_json
            )
            db.foodfinder.commit()

            print(f"+ Menu data imported to FoodFinder")

        except Exception as e:
            print(f"! FoodFinder sync warning: {e}")

        print()

        # Step 7: Display summary
        print("=" * 80)
        print("SCRAPING TEST COMPLETE")
        print("=" * 80)
        print(f"Restaurant: {restaurant_name}")
        print(f"URL: {url}")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Status: {'SUCCESS' if result_dict.get('success') else 'FAILED'}")
        print(f"Categories: {category_count}")
        print(f"Menu Items: {len(items)}")
        print(f"Items with Prices: {items_with_prices} ({items_with_prices/len(items)*100:.1f}%)" if items else "N/A")
        print(f"Confidence: {result_dict.get('confidence_score', 0):.2f}")
        print(f"Method: {result_dict.get('extraction_method', 'N/A')}")
        print(f"Completed: {datetime.now()}")
        print("=" * 80)

        # Save detailed results to file
        output_file = f"bubba_menu_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, indent=2, ensure_ascii=False)
        print(f"\n+ Detailed results saved to: {output_file}")

        return result

    except Exception as e:
        duration = time.time() - start_time
        print(f"\n- Menu extraction failed after {duration:.2f} seconds")
        print(f"Error: {e}")

        # Mark job as failed
        try:
            db.complete_job(
                job_id=job_id,
                status='failed',
                processing_time_seconds=duration,
                error_message=str(e)
            )
            print(f"+ Job marked as failed in database")
        except:
            pass

        import traceback
        traceback.print_exc()

        return None


if __name__ == "__main__":
    test_bubbas_menu_scrape()
