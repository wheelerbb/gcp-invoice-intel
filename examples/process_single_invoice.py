from src.main import InvoiceProcessor

def main():
    processor = InvoiceProcessor(use_gemini=False)
    result = processor.process_invoice("path/to/invoice.pdf")
    print(f"Processed Invoice: {result}")

if __name__ == "__main__":
    main() 