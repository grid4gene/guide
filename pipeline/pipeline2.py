#!/usr/bin/env python

# Copyright (c) 2017-2018 Breakthrough Genomics Ltd. (Martin Triska)
#
# Following code is proprietary and any use without explicit permission
# from Breakthrough Genomics Ltd. is forbidden


import sys
import subprocess
import logging

### PATH DEFINITIONS #############################################################################

base_folder = "/home/test/WGS_pipeline/"
tools_dir = base_folder+"TOOLS/"
reference_dir = base_folder+"reference/"
output_folder = base_folder+"TEST/output/"
gatk_binary = "gatk"
bowtie2_binary = tools_dir+"bowtie2-2.3.4.1-linux-x86_64/bowtie2"
samtools_binary = tools_dir + "samtools-1.8/samtools"
bowtie2_index = reference_dir+"hg19"
reference_fasta = reference_dir+"hg19.fasta"
dbsnp_vcf = reference_dir+"dbsnp_138.hg19.vcf"

### END OF PATH DEFINITIONS ######################################################################

class pipeline():
  def __init__(self, sample_name, f1, f2):
    self.sample_name = sample_name
    self.fastq1 = f1
    self.fastq2 = f2
    self.threads = "136"
    self.open_files = []
    self.docker_image = "broadinstitute/gatk:4.0.5.2"
    #self.docker_image = "broadinstitute/gatk:4.0.2.0"
    # logger setup
    LOG_FORMAT = "%(levelname)s\t%(asctime)s\t%(module)s\t%(funcName)s\t%(message)s"
    logging.basicConfig(filename = None,
                        level = logging.DEBUG,
                        format = LOG_FORMAT)
    self.logger = logging.getLogger()

  def close_all_files(self):
    for f in self.open_files:
        f.close()

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

    errcode = subprocess.call(dcmd, stdout=stdout, stderr=stderr)
    if errcode != 0:
      self.close_all_files()
      raise RuntimeError("Failed: {}".format(" ".join(dcmd)))
    self.close_all_files()

  def run_pipeline(self):

    # Align to reference genome (bowtie2) and sort (samtools)
    bowtie2_cmd = [bowtie2_binary]
    bowtie2_cmd += ["-x", bowtie2_index]
    bowtie2_cmd += ["-1", self.fastq1]
    bowtie2_cmd += ["-2", self.fastq2]
    bowtie2_cmd += ["-p", self.threads]
    bowtie2_err = output_folder+self.sample_name+".bowtie2.err"

    sort_cmd = [samtools_binary, "sort"]
    sort_cmd += ["-@", "2"]
    sorted_bam = output_folder+self.sample_name+".bowtie2.bam"
    sort_err = output_folder+self.sample_name+".sort.err"

    print sort_cmd

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

    # Mark duplicates (GATK)
    markDuplicates_bam =     output_folder+self.sample_name+".MarkDuplicates.bam"
    markDuplicates_metrics = output_folder+self.sample_name+".MarkDuplicates-metrics.txt"
    markDuplicates_cmd = [gatk_binary, "MarkDuplicates"]
    markDuplicates_cmd += ["-I", sorted_bam]
    markDuplicates_cmd += ["-O", markDuplicates_bam]
    markDuplicates_cmd += ["-M", markDuplicates_metrics]
    markDuplicates_log = output_folder+self.sample_name+".MarkDuplicates.log"
    self.run_in_docker(markDuplicates_cmd, stderr=markDuplicates_log)

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
    self.run_in_docker(ReadGroups_cmd, stderr=ReadGroups_log)

    # Base recalibrator (GATK)
    BaseRecalibrator_metrics = output_folder+self.sample_name+".BaseRecalibrator-metrics.txt"
    BaseRecalibrator_cmd = [gatk_binary, "BaseRecalibrator"]
    BaseRecalibrator_cmd += ["-I", ReadGroups_bam]
    BaseRecalibrator_cmd += ["-O", BaseRecalibrator_metrics]
    BaseRecalibrator_cmd += ["-R", reference_fasta]
    BaseRecalibrator_cmd += ["--known-sites", dbsnp_vcf]
    BaseRecalibrator_log = output_folder+self.sample_name+".BaseRecalibrator.log"
    self.run_in_docker(BaseRecalibrator_cmd, stderr=BaseRecalibrator_log)

    # Base recalibrator - applying model (GATK)
    BaseRecalibrator_bam = output_folder+self.sample_name+".BaseRecalibrator.bam"
    ApplyBQSR_cmd = [gatk_binary, "ApplyBQSR"]
    ApplyBQSR_cmd += ["-I", ReadGroups_bam]
    ApplyBQSR_cmd += ["-bqsr", BaseRecalibrator_metrics]
    ApplyBQSR_cmd += ["-O", BaseRecalibrator_bam]
    ApplyBQSR_log = output_folder+self.sample_name+".ApplyBQSR.log"
    self.run_in_docker(ApplyBQSR_cmd, stderr=ApplyBQSR_log)

    # Haplotype caller
    vcf = output_folder+self.sample_name+".vcf.gz"
    HaplotypeCaller_cmd = [gatk_binary, "HaplotypeCaller"]
    HaplotypeCaller_cmd += ["-I", BaseRecalibrator_bam]
    HaplotypeCaller_cmd += ["-O", vcf]
    HaplotypeCaller_cmd += ["-R", reference_fasta]
    HaplotypeCaller_log = output_folder+self.sample_name+".HaplotypeCaller.log"
    self.run_in_docker(HaplotypeCaller_cmd, stderr=HaplotypeCaller_log)
