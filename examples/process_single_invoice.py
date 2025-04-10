from src.main import InvoiceProcessor
import os

def main():
    try:
        # Initialize the processor with use_gemini=False
        processor = InvoiceProcessor(use_gemini=False)
        
        # Process a sample invoice
        sample_invoice = "samples/invoices/WHITE - ASAP Site Services - Port o let 04.30.23.pdf"
        if not os.path.exists(sample_invoice):
            print(f"Error: Sample invoice not found at {sample_invoice}")
            return
            
        print(f"Processing invoice: {sample_invoice}")
        result = processor.process_invoice(sample_invoice)
        print(f"Processed Invoice: {result}")
        
    except Exception as e:
        print(f"Error processing invoice: {str(e)}")

if __name__ == "__main__":
    main() 