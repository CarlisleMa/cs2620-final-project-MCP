# utils/generate_proto.py
import os
import sys
import subprocess

def generate_proto(proto_file, output_dir="."):
    """Generate Python code from protocol buffer definition"""
    try:
        # Check if protoc is installed
        subprocess.check_call(["protoc", "--version"], stdout=subprocess.PIPE)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: protoc compiler not found. Please install protobuf compiler.")
        return False
    
    try:
        # Generate Python code
        subprocess.check_call([
            "python", "-m", "grpc_tools.protoc",
            f"--proto_path={os.path.dirname(proto_file)}",
            f"--python_out={output_dir}",
            f"--grpc_python_out={output_dir}",
            os.path.basename(proto_file)
        ])
        
        print(f"Generated Python code from {proto_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error generating code: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_proto.py <proto_file> [output_dir]")
        sys.exit(1)
    
    proto_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "."
    
    if not generate_proto(proto_file, output_dir):
        sys.exit(1)