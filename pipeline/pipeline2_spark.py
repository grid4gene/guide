#!/usr/bin/env python

# Copyright (c) 2017-2018 Breakthrough Genomics Ltd. (Martin Triska)
# 
# Following code is proprietary and any use without explicit permission
# from Breakthrough Genomics Ltd. is forbidden

import sys
import subprocess
import logging

### PATH DEFINITIONS #############################################################################
hdfs_url = "hdfs://wolfpass-aep:9000/user/test/"

base_folder = "/home/test/WGS_pipeline/"
tools_dir = base_folder+"TOOLS/"
reference_dir = base_folder+"reference/"
output_folder = base_folder+"TEST/output/"
gatk_binary = "gatk"
bowtie2_binary = tools_dir+"bowtie2-2.3.4.1-linux-x86_64/bowtie2"
samtools_binary = tools_dir + "samtools-1.8/samtools"
bowtie2_index = reference_dir+"hg19"
reference_fasta = reference_dir+"hg19.fasta"
reference_fasta_2bit = hdfs_url+"hg19.2bit"
dbsnp_vcf = reference_dir+"dbsnp_138.hg19.vcf"
hdfs_url = "hdfs://wolfpass-aep:9000/user/test/"

    
#define the number of logic cpu core in the server
num_cores = "104"
#spark_parmeters = ["--", "--spark-master",  "local[20]"]
#spark_parmeters = ["--", "--spark-runner",  "LOCAL"]
spark_parmeters = ["--", "--spark-runner",  "SPARK", "--spark-master", "yarn", "--deploy-mode", "cluster",
#"--spark-submit-command", "spark-submit", "--num-executors", "4", "--executor-cores", "4", "--executor-memory", "12g", "--driver-memory", "4g"]
"--spark-submit-command", "spark-submit", "--executor-memory", "12g", "--driver-memory", "4g"]
### END OF PATH DEFINITIONS ######################################################################

class pipeline():
  def __init__(self, sample_name, f1, f2):
    self.sample_name = sample_name
    self.fastq1 = f1
    self.fastq2 = f2
    self.threads = num_cores
    self.open_files = []
    self.docker_image = "broadinstitute/gatk:4.0.6.0"

    #define the read group parameter
    self.rg_id = "1"
    self.rg_pu = "PU:unit1"
    self.rg_pl = "PL:Illumina"
    self.rg_sm = "SM:" + self.sample_name
    self.rg_lb = "LB:" + "lib1"

    # logger setup
    LOG_FORMAT = "%(levelname)s\t%(asctime)s\t%(module)s\t%(funcName)s\t%(message)s"
    logging.basicConfig(filename = None,
                        level = logging.DEBUG,
                        format = LOG_FORMAT)
    self.logger = logging.getLogger()
  
  def close_all_files(self):
    for f in self.open_files:
        f.close()

  def run_in_local(self, cmd, stdout=None, stderr=None):
    """ Run a command in local host"""
    print cmd
    if stdout is not None:
      stdout = open(stdout,"w")
      self.open_files.append(stdout)
    if stderr is not None:
      stderr = open(stderr,"w")
      self.open_files.append(stderr)
    errcode = subprocess.call(cmd, stdout=stdout, stderr=stderr)
    if errcode != 0:
      self.close_all_files()
      raise RuntimeError("Failed: {}".format(" ".join(cmd)))
    self.close_all_files()
  
  def run_in_docker(self, cmd, stdout=None, stderr=None):
    """ Run a command inside docker container"""
    dcmd = ["sudo", "docker", "run",
            "-v", "{}:{}".format(base_folder, base_folder),
            self.docker_image]
    dcmd += cmd
    if stdout is not None:
      stdout = open(stdout,"w")
      self.open_files.append(stdout)
    if stderr is not None:
      stderr = open(stderr,"w")
      self.open_files.append(stderr)
    self.logger.info("Running: "+" ".join(dcmd))
    
    print dcmd
    errcode = subprocess.call(dcmd, stdout=stdout, stderr=stderr)
    if errcode != 0:
      self.close_all_files()
      raise RuntimeError("Failed: {}".format(" ".join(dcmd)))
    self.close_all_files()
  
  def run_pipeline(self):  
    global output_folder  
    # Align to reference genome (bowtie2) and sort (samtools)
    bowtie2_cmd = [bowtie2_binary]
    bowtie2_cmd += ["-x", bowtie2_index]
    bowtie2_cmd += ["-1", self.fastq1]
    bowtie2_cmd += ["-2", self.fastq2]
    bowtie2_cmd += ["-p", self.threads]
    bowtie2_cmd += ["--rg-id", self.rg_id]
    bowtie2_cmd += ["--rg", self.rg_pu]
    bowtie2_cmd += ["--rg", self.rg_pl]
    bowtie2_cmd += ["--rg", self.rg_sm]
    bowtie2_cmd += ["--rg", self.rg_lb]

    bowtie2_err = output_folder+self.sample_name+".bowtie2.err"
    
    sort_cmd = [samtools_binary, "sort"]
    sort_cmd += ["-@", "104"]
    sorted_bam = output_folder+self.sample_name+".bowtie2.bam"
    sorted_bam_hdfs = hdfs_url+self.sample_name+".bowtie2.bam"
    sort_err = output_folder+self.sample_name+".sort.err"
    
    print sort_cmd
    """
    with open(sorted_bam,"w") as f_sorted_bam:
      with open(sort_err,"w") as f_sort_err:
        with open(bowtie2_err,"w") as f_bowtie2_err:
          self.logger.info("Running: "+" ".join(bowtie2_cmd)+" | "+" ".join(sort_cmd)+" > "+sorted_bam)
          bowtie2_process = subprocess.Popen(bowtie2_cmd,
                                             stdout=subprocess.PIPE,
                                             stderr=f_bowtie2_err)
          sort_process = subprocess.Popen(sort_cmd,
                                          stdin=bowtie2_process.stdout,
                                          stdout=f_sorted_bam,
                                          stderr=f_sort_err)
          sort_process.communicate()
    """

    #move the data to hdfs
    cp_to_hdfs_cmd = ["hdfs", "dfs"]
    cp_to_hdfs_cmd += ["-put", sorted_bam, sorted_bam_hdfs]
    print cp_to_hdfs_cmd
    #subprocess.check_output(cp_to_hdfs_cmd)

    # Mark duplicates (GATK)
    #markDuplicates_bam =     output_folder+self.sample_name+".MarkDuplicates.bam"
    #markDuplicates_metrics = output_folder+self.sample_name+".MarkDuplicates-metrics.txt"
    markDuplicates_bam_hdfs =     hdfs_url+self.sample_name+".MarkDuplicates.bam"
    markDuplicates_metrics_hdfs = hdfs_url+self.sample_name+".MarkDuplicates-metrics.txt"
    markDuplicates_cmd = [gatk_binary, "MarkDuplicatesSpark"]
    markDuplicates_cmd += ["-I", sorted_bam_hdfs]
    markDuplicates_cmd += ["-O", markDuplicates_bam_hdfs]
    markDuplicates_cmd += ["-M", markDuplicates_metrics_hdfs]
    markDuplicates_cmd += spark_parmeters
    markDuplicates_log = output_folder+self.sample_name+".MarkDuplicates.log"
    #self.run_in_local(markDuplicates_cmd, stderr=markDuplicates_log)
    
    """
    Don't need the add read group as we add it in the bowtie2

    # Add read groups (GATK)
    ReadGroups_bam =     output_folder+self.sample_name+".ReadGroups.bam"
    ReadGroups_cmd = [gatk_binary, "AddOrReplaceReadGroups"]
    ReadGroups_cmd += ["-I", markDuplicates_bam]
    ReadGroups_cmd += ["-O", ReadGroups_bam]
    ReadGroups_cmd += ["--RGLB", "lib1"]
    ReadGroups_cmd += ["--RGPL", "Illumina"]
    ReadGroups_cmd += ["--RGPU", "unit1"]
    ReadGroups_cmd += ["--RGSM", self.sample_name]
    ReadGroups_log = output_folder+self.sample_name+".ReadGroups.log"
    #self.run_in_docker(ReadGroups_cmd, stderr=ReadGroups_log)
    self.run_in_local(ReadGroups_cmd, stderr=ReadGroups_log)
    """

    # Base recalibrator (GATK)
    #BaseRecalibrator_metrics = output_folder+self.sample_name+".BaseRecalibrator-metrics.txt"
    BaseRecalibrator_metrics_hdfs = hdfs_url+self.sample_name+".BaseRecalibrator-metrics.txt"
    BaseRecalibrator_cmd = [gatk_binary, "BaseRecalibratorSpark"]
    BaseRecalibrator_cmd += ["-I", markDuplicates_bam_hdfs]
    BaseRecalibrator_cmd += ["-O", BaseRecalibrator_metrics_hdfs]
    BaseRecalibrator_cmd += ["-R", reference_fasta_2bit]
    BaseRecalibrator_cmd += ["--known-sites", dbsnp_vcf]
    BaseRecalibrator_cmd += spark_parmeters
    BaseRecalibrator_log = output_folder+self.sample_name+".BaseRecalibrator.log"
    #self.run_in_local(BaseRecalibrator_cmd, stderr=BaseRecalibrator_log)
    
    # Base recalibrator - applying model (GATK)
    #BaseRecalibrator_bam = output_folder+self.sample_name+".BaseRecalibrator.bam"
    BaseRecalibrator_bam_hdfs = hdfs_url+self.sample_name+".BaseRecalibrator.bam"
    ApplyBQSR_cmd = [gatk_binary, "ApplyBQSRSpark"]
    ApplyBQSR_cmd += ["-I", markDuplicates_bam_hdfs]
    ApplyBQSR_cmd += ["-bqsr", BaseRecalibrator_metrics_hdfs]
    ApplyBQSR_cmd += ["-O", BaseRecalibrator_bam_hdfs]
    ApplyBQSR_cmd += spark_parmeters
    ApplyBQSR_log = output_folder+self.sample_name+".ApplyBQSR.log"
    self.run_in_local(ApplyBQSR_cmd, stderr=ApplyBQSR_log)
    
    # Haplotype caller
    #vcf = output_folder+self.sample_name+".vcf.gz"
    vcf_hdfs = output_folder+self.sample_name+".vcf.gz"
    HaplotypeCaller_cmd = [gatk_binary, "HaplotypeCallerSpark"]
    HaplotypeCaller_cmd += ["-I", BaseRecalibrator_bam_hdfs]
    HaplotypeCaller_cmd += ["-O", vcf_hdfs]
    HaplotypeCaller_cmd += ["-R", reference_fasta]
    HaplotypeCaller_cmd += spark_parmeters
    HaplotypeCaller_log = output_folder+self.sample_name+".HaplotypeCaller.log"
    self.run_in_local(HaplotypeCaller_cmd, stderr=HaplotypeCaller_log)

    print "end of WGS"
