from src.main import InvoiceProcessor
import os
import sys
import argparse

def main():
    try:
        # Set up argument parser
        parser = argparse.ArgumentParser(description='Process a single invoice with optional Gemini enhancement')
        parser.add_argument('invoice_path', help='Path to the invoice PDF file')
        parser.add_argument('--no-gemini', action='store_true', help='Disable Gemini processing')
        
        args = parser.parse_args()
        
        # Check if invoice exists
        if not os.path.exists(args.invoice_path):
            print(f"Error: Invoice not found at {args.invoice_path}")
            return
            
        # Initialize the processor (use Gemini by default unless --no-gemini is specified)
        processor = InvoiceProcessor(use_gemini=not args.no_gemini)
        
        print(f"Processing invoice: {args.invoice_path}")
        print(f"Gemini processing: {'disabled' if args.no_gemini else 'enabled'}")
        result = processor.process_invoice(args.invoice_path)
        print(f"Processed Invoice: {result}")
        
    except Exception as e:
        print(f"Error processing invoice: {str(e)}")

if __name__ == "__main__":
    main() 