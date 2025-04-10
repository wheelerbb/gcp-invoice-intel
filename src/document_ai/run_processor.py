from simple_processor import SimpleInvoiceProcessor
import sys

def main():
    if len(sys.argv) != 2:
        print("Usage: python run_processor.py <path_to_invoice_pdf>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    processor = SimpleInvoiceProcessor()
    
    try:
        result = processor.process_document(file_path)
        print("Processed Invoice Data:")
        print(result)
    except Exception as e:
        print(f"Error processing document: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 