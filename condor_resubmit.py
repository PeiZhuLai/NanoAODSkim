import os
from ROOT import TFile
import re
import subprocess
import argparse

"""Condor resubmit script.

# Three steps to submit condor script

1. Get the list of jobs from the condor jdl file and the expected output root files
2. Get the list of output root files from the output directory
   1. Check if these root files are good and have entries, if not, mark them as bad or remove them from the correct output root file list
3. Compare the two lists and find the missing root files
4. Get a list of jobs to be submitted from step 2 and 3.
5. Prepare a new condor jdl file with the list of jobs from step 4.
6. Submit the new condor jdl file.
"""

def get_map_from_stdout_files(cluster_id, log_path):
    """Get the map from all *.stdout files based on two strings: "Input MiniAOD File" and "Output NanoAOD File".

    Args:
        cluster_id (int): Condor cluster ID.
        log_path (str): Path to the log files.

    Returns:
        dict: Map from all *.stdout files based on two strings: "Input MiniAOD File" and "Output NanoAOD File".
    """
    map = {}
    outfiltlist = []
    for file in os.listdir(log_path):
        if file.endswith(".stdout") and str(cluster_id) in file:
            print("file: {0}".format(file))
            with open(os.path.join(log_path, file)) as f:
                datafile = f.readlines()
                for line in datafile:
                    if "Input MiniAOD File" in line:
                        split_line = line.split()
                        infile = split_line[-1]
                    elif "Output NanoAOD File" in line:
                        split_line = line.split()
                        outfile = split_line[-1]
                        outfiltlist.append(outfile)
                map[outfile] = infile
                print("infile: {0}, outfile: {1}".format(infile, outfile))
                print("map: {0}".format(map)  )
    return outfiltlist, map

def get_root_files_from_dir(directory, map):
    """Get the list of output root files from the output directory.

    Args:
        directory (str): Path to the output directory.

    Returns:
        list: List of output root files.
    """
    print("directory: {0}".format(directory))

    # check if they are not corrupted and have entries
    filelist_to_remove = []

    root_files = []
    ValidRootFiles = []
    # for dirpath, dirnames, filenames in os.walk(directory):
    #     for filename in filenames:
    #         if filename.endswith('.root'):
    #             full_path = os.path.join(dirpath, filename)
    #             # print('Checking file: '+full_path)
    #             root_files.append(full_path)

    #             tfile = None
    
    for filename, full_path in map.items():
            try:
                tfile = TFile.Open(full_path);
            except:
                pass
            if tfile:
                if (tfile.IsZombie() or tfile.TestBit(TFile.kRecovered) or tfile.GetListOfKeys().IsEmpty()):

                    filelist_to_remove.append(filename)
                else:
                    ValidRootFiles.append(filename)
            else:
                # print('File could not be opened, adding it to missing files')
                filelist_to_remove.append(filename)

    print("Total root file in the directory: {0}".format(len(root_files)))
    print("length of corrupted root files: {0}".format(len(filelist_to_remove)))
    print("length of ValidRootFiles: {0}".format(len(ValidRootFiles)))
    # print('Removing the following files from the list of root files: ')
    # print(filelist_to_remove)

    return ValidRootFiles

def get_missing_files(job_list, root_file_list):
    """Compare the two lists and find the missing root files.

    Args:
        job_list (list): List of jobs.
        root_file_list (list): List of output root files.

    Returns:
        list: List of missing root files.
    """
    missing = []
    for job in job_list:
        if job not in root_file_list:
            missing.append(job)
    return missing



def submit_new_jdl_file(jdl_file):
    """Submit the new condor jdl file.

    Args:
        jdl_file (str): Path to the condor jdl file.
    """
    bashCommand = "condor_submit %s"%(jdl_file)
    os.system(bashCommand)

def get_output_files_from_jdl(path_jdl):
    """Open the JDL file and grab the list of output root files specified in the Arguments lines at the 5th position

    Argument line format:

    Arguments = $(Cluster) $(Process)   DATA-Run2018-NanoAODv9-02546_1_cfg.py /store/data/Run2018A/EGamma/MINIAOD/UL2018_MiniAODv2_GT36-v1/60001/46BBF05E-C770-7949-A8CD-D850D6FE8C15.root 46BBF05E-C770-7949-A8CD-D850D6FE8C15.root root://eosuser.cern.ch//eos/user/r/rasharma/post_doc_ihep/double-higgs/nanoAODnTuples/nanoAOD_Mar2024/UL2018/EGamma_Run2018A

    Args:
        path_jdl (str): JDL file with its path

    Returns:
        list: list having list of output root files specified at the 5th position in Arguments lines
    """
    output_root_files = []

    with open(path_jdl) as myfile:
        lines = myfile.readlines()

    map = {}
    for line in lines:
        if line.startswith('Arguments ='):
            parts = line.split()
            if len(parts) > 4:             
                # Assuming the 5th position (=4 in array) is always a root file as per the given format
                # split will also add Arguments and = as two strings in the list so instead of 4, 6 is used
                output_root_file = parts[2].split("/")[-1]
                output_root_files.append(output_root_file)
                map[output_root_file] = parts[3]

    return output_root_files, map

def prepare_runJobs_missing(FailedJobRootFile,InputJdlFile,CondorLogDir,EOSDir,Resubmit_no, attach_job_id, DEBUG=False):
    if DEBUG: print("FailedJobRootFile: {}".format(FailedJobRootFile))
    if DEBUG: print("InputJdlFile: {}".format(InputJdlFile))
    if DEBUG: print("CondorLogDir: {}".format(CondorLogDir))
    if DEBUG: print("EOSDir: {}".format(EOSDir))

    bashCommand = "cp {0}  original_{1}".format(InputJdlFile, InputJdlFile.split('/')[-1])
    if DEBUG: print("copy command: {}".format(bashCommand))
    os.system(bashCommand)

    outjdl_fileName = (InputJdlFile.split('/')[-1]).replace(".jdl", "_resubmit_"+str(Resubmit_no)+".jdl")
    print("outjdl_fileName: {}".format(outjdl_fileName))
    outjdl_file = open(outjdl_fileName,"w")

    with open(InputJdlFile, 'r') as myfile:
        """Copy the main part of original jdl file to new jdl file.
        All the lines before "Output = " should be copied to new jdl file.
        """
        for line in myfile:
            # Check if line starts with "Output = "
            if line.startswith("Output = "):
                break
            outjdl_file.write(line)

    for RootFiles in FailedJobRootFile:
        match = None
        OldRefFile = ""
        if DEBUG: print("Root file to look for in stdout files: {}".format(RootFiles))
        bashCommand = "grep {} {}/*.stdout".format(RootFiles, CondorLogDir)
        if DEBUG: print("grep command: {}".format(bashCommand))
        if attach_job_id:
            grep_stdout_files = os.popen(bashCommand).read()
            if DEBUG: print("{}\n{}\n{}".format("="*51,grep_stdout_files,"="*51))

            # Regular expression to match paths ending with .stdout
            stdout_file_pattern = re.compile(r'\S+\.stdout')

            # Search for the .stdout file path in the output
            match = stdout_file_pattern.search(grep_stdout_files)
            # print("===")
            # print("grep command: {}".format(bashCommand))
            # print("{}".format(grep_stdout_files))
            # print("Match: {}".format(match))

        if match:
            stdout_file_path = match.group()
            if DEBUG: print(stdout_file_path.strip())
            OldRefFile = stdout_file_path.strip().split("/")[-1].replace(".stdout","").split("_")[-1]
        else:
            if DEBUG: print("No .stdout file path found in the output.")
            OldRefFile = ""
        if DEBUG: print("OldRefFile: {}".format(OldRefFile))

        grepCommand_GetJdlInfo = 'grep -A1 -B3 "{}" {}'.format(RootFiles, InputJdlFile)
        if DEBUG: print(grepCommand_GetJdlInfo)
        grep_condor_jdl_part = os.popen(grepCommand_GetJdlInfo).read()
        if DEBUG: print("=="*51)
        if DEBUG: print(grep_condor_jdl_part)
        updateString = grep_condor_jdl_part.replace('$(Process)',OldRefFile+'_$(Process)'+ '_resubmit_' +Resubmit_no)
        if DEBUG: print("=="*51)
        if DEBUG: print(updateString)
        if DEBUG: print("=="*51)
        outjdl_file.write(updateString)
    outjdl_file.close()
    return outjdl_fileName

def get_condor_job_details(job_id, DEBUG=False):
    """
    Grabs a list of all Condor jobs associated with a specific job ID,
    then extracts the specified arguments from each job's command.

    Expected condor_q output:
    2889644.0   rasharma        3/21 14:22   0+00:00:00 I  0      0.0 HHbbgg_Signal_Mar2024.sh 2889644 0 DATA-Run2018-NanoAODv9-02546_1_cfg.py /store/data/Run2018A/EGamma/MINIAOD/UL2018_MiniAODv2_GT36-v1/60001/46BBF05E-C770-7949-A8CD-D850D6FE8C15.root 46BBF05E-C770-7949-A8CD-D850D6FE8C15.root root://eosuser.cern.ch//eos/user/r/rasharma/post_doc_ihep/double-higgs/nanoAODnTuples/nanoAOD_Mar2024/UL2018/EGamma_Run2018A
    2889644.1   rasharma        3/21 14:22   0+00:00:00 I  0      0.0 HHbbgg_Signal_Mar2024.sh 2889644 1 DATA-Run2018-NanoAODv9-02546_1_cfg.py /store/data/Run2018A/EGamma/MINIAOD/UL2018_MiniAODv2_GT36-v1/60001/RAM_46BBF05E-C770-7949-A8CD-D850D6FE8C15.root RAM_46BBF05E-C770-7949-A8CD-D850D6FE8C15.root root://eosuser.cern.ch//eos/user/r/rasharma/post_doc_ihep/double-higgs/nanoAODnTuples/nanoAOD_Mar2024/UL2018/EGamma_Run2018A

    Parameters:
    - job_id: The ID of the Condor jobs to filter by.

    Returns:
    A list of tuples, each containing the extracted arguments for each job matching the job ID.
    """
    # Execute the condor_q command and capture its output
    command = 'condor_q -nobatch'
    result = subprocess.check_output(command, shell=True)

    # Decode result to convert bytes to str (for Python 3 compatibility)
    result_str = result.decode('utf-8')
    if DEBUG: print("{}\n {}\n{}".format("="*51,result_str,"="*51))

    # Initialize an empty list to hold the extracted details
    job_details = []

    for line in result_str.split('\n'):
        print("line: {}".format(line))
        # Get 2nd last and last arguments from the command

        # check if job_id is in the line
        # if str(job_id) in line:
        if len(line.split()) > 10 and str(job_id) in line:
            job_details.append(line.split()[-2])

    if DEBUG: print("{}\n {}\n{}".format("="*51,job_details,"="*51))
    return job_details

def submit_missing(InputJdlFile,resubmit=True):
    bashCommand = "condor_submit {}".format(InputJdlFile)
    if resubmit :
        print('Resubmitting now!')
        os.system(bashCommand)
    else :
        print('Ready to resubmit, please set resubmit to True if you are ready : ')
        print(bashCommand)

def main():
    """Main function.
    """
    # Add argparse to get the input arguments
    parser = argparse.ArgumentParser(description='Condor resubmit script.')
    parser.add_argument('-j', '--jdl_file', help='JDL file with path', required=True)
    parser.add_argument('-l', '--CondorLogDir', help='Path to the log files', required=True)
    parser.add_argument('-o', '--output_dir', help='Path to the output directory', required=True)
    parser.add_argument("-c", "--condor_job_id", dest="condor_job_id",default="",help="condor job id")
    parser.add_argument("-n", "--resubmit_no", dest="resubmit_no",default=1,help="resubmit counter")
    parser.add_argument("-d", "--debug", dest="debug",default=False,help="debug")
    parser.add_argument("-a", "--attach_job_id", dest="attach_job_id",default=False,help="attach job id to new job log files, this may help to compare the log files")
    args = parser.parse_args()

    jdl_file = args.jdl_file
    CondorLogDir = args.CondorLogDir
    output_dir = args.output_dir
    condor_job_id = args.condor_job_id

    # Step - 1: Get the root file information from the jdl file
    root_file_list_from_jdl, map_in_out_files = get_output_files_from_jdl(jdl_file)
    print("length of root_file_list_from_jdl: {0}".format(len(root_file_list_from_jdl)))
    if args.debug: print("root_file_list_from_jdl: {0}".format(root_file_list_from_jdl))

    # Step - 2: Get the root file information from the output directory
    root_file_list = get_root_files_from_dir(output_dir, map_in_out_files)
    print("length of root_file_list: {0}".format(len(root_file_list)))
    # print("root_file_list: {0}".format(root_file_list))
    if args.debug: print("root_file_list: {0}".format(root_file_list))
    modified_list = [filename.replace('_skimmed', '') for filename in root_file_list]
    
    # Step - 3: Compare the two lists and find the missing root files
    # missing = list(set(root_file_list_from_jdl) - set(root_file_list))
    missing = list(set(root_file_list_from_jdl) - set(modified_list))
    print("length of missing: {0}".format(len(missing)))
    if args.debug: print("missing: {0}".format(missing))

    # If the condor jobs are still running then remove the files over which condor jobs are running from the list "missing"
    if condor_job_id:
        details = get_condor_job_details(condor_job_id, args.debug)
        print('Number of condor jobs running : {}'.format(len(details)))
        if args.debug: print('Condor jobs running : {}'.format(details))
        if args.debug: print('Missing files : {}'.format(missing))
        missing = list(set(missing) - set(details))

        print('Number of missing files (after removing the files over which condor jobs are running) : {}'.format(len(missing)))
        if args.debug: print('Missing files (after removing the files over which condor jobs are running) : {}'.format(missing))


    # Step - 3: Prepare the new jdl file
    jdl_file = prepare_runJobs_missing(missing, jdl_file, CondorLogDir, output_dir, str(1), args.attach_job_id, args.debug)

    # Print summary of files:
    print("====================================")
    print("Summary of files:")
    print("length of root_file_list_from_jdl: {0}".format(len(root_file_list_from_jdl)))
    print("length of root_file_list from output directory: {0}".format(len(root_file_list)))
    print("length of missing files: {0}".format(len(missing)))
    print("====================================")

    # Step - 4: Submit the new jdl file
    print('Submitting missing jobs : ')
    submit_missing(jdl_file,0)

if __name__ == "__main__":
    main()