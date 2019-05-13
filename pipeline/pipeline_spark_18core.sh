#!/bin/bash
set -x

export base="/home"
export input="$base/input"
export output="$base/output"
export reference="/reference"
export tools="/mnt/disk_a/tools"

export sample="412"
#input file
export R1="$input/${sample}_1.fastq.gz"
export R2="$input/${sample}_2.fastq.gz"
#reference file
export hg19_bwa="$base/$reference/hg19.fasta"
export hg19="$reference/hg19.fasta"
export dir_vcf="$reference"
export bed="$reference/Agilent_S06588914_Covered.bed"
#output file
export dir_analyzed_sample="$output"
export sp_name="pipe-4.0-spark-"$sample
#tools
export dir_bin="$tools"

export hdfs_url=localhost:9000/user/root
export spark_tools="/mnt/disk_a/spark_tools"

export spark_cmd="-- --spark-runner SPARK --spark-master yarn --deploy-mode cluster \
    --driver-memory 4g \
    --num-executors 4 --executor-cores 8 --executor-memory 30g \
    --conf spark.yarn.executor.memoryOverhead=600 
    --conf spark.local.dir=/home/hdfs/spark"

export threads=18
export cores=18

if false
then
# Align the reads
time bash -c "taskset -c 0-17 ${dir_bin}/bwa mem  -t $threads  $hg19_bwa  $R1 $R2 | ${dir_bin}/samtools view -@ $threads -S -b > $dir_analyzed_sample/$sp_name-bwa.bam"
# filter reads un-mapped reads and sort bam file
time bash -c "taskset -c 0-17 ${dir_bin}/samtools view -@ $cores -b -h  -F 4 $dir_analyzed_sample/$sp_name-bwa.bam  > $dir_analyzed_sample/$sp_name-ali.bam"

# Sorting BAM
time bash -c "taskset -c 0-17  ${dir_bin}/samtools sort -@ $cores $dir_analyzed_sample/$sp_name-ali.bam  -o $dir_analyzed_sample/$sp_name-ali-sorted.bam"

# Add ReadGroup
time bash -c "taskset -c 0-17  java -jar ${dir_bin}/picard.jar AddOrReplaceReadGroups  I=$dir_analyzed_sample/$sp_name-ali-sorted.bam  O=$dir_analyzed_sample/$sp_name-ali-sorted-RG.bam  RGSM=$sp_name RGLB=project RGPL=illumina RGID=none RGPU=none VALIDATION_STRINGENCY=LENIENT"
fi

hdfs dfs -rm $sp_name-*
hdfs dfs -put $dir_analyzed_sample/$sp_name-ali-sorted-RG.bam

# Remove duplicates
#time bash -c "gatk MarkDuplicatesSpark  --remove-all-duplicates false --create-output-bam-index --read-validation-stringency LENIENT -I hdfs://$hdfs_url/$sp_name-ali-sorted-RG.bam  -O hdfs://$hdfs_url/$sp_name-ali-sorted-RG-rmdup.bam  --metrics-file hdfs://$hdfs_url/$sp_name-pacard.metrics $spark_cmd"
#no metric for high perforamnce
date
gatk MarkDuplicatesSpark  --remove-all-duplicates false --create-output-bam-index --read-validation-stringency LENIENT -I hdfs://$hdfs_url/$sp_name-ali-sorted-RG.bam  -O hdfs://$hdfs_url/$sp_name-ali-sorted-RG-rmdup.bam $spark_cmd



# index BAM
#time bash -c "taskset -c 0-17  ${dir_bin}/samtools index -@ $cores $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup.bam"


#RealignerTargetCreator and IndelRealigner were removed from GATK 4.0 best practics

# RealignerTargetCreator
#time bash -c "taskset -c 0-17  java -jar $dir_bin/GenomeAnalysisTK.jar -nt $cores -T RealignerTargetCreator -known $dir_vcf/Mills_and_1000G_gold_standard.indels.hg19.sites.vcf  -known $dir_vcf/1000G_phase1.indels.hg19.sites.vcf  -R $hg19 -I $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup.bam -o $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup.bam.list"

# IndelRealigner
#time bash -c "taskset -c 0-17  java -jar $dir_bin/GenomeAnalysisTK.jar  -T IndelRealigner -known $dir_vcf/Mills_and_1000G_gold_standard.indels.hg19.sites.vcf -known $dir_vcf/1000G_phase1.indels.hg19.sites.vcf -R $hg19 -I $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup.bam -targetIntervals $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup.bam.list -o $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup-realigned.bam"

#BaseRecalibrator
date
gatk BQSRPipelineSpark -I hdfs://$hdfs_url/$sp_name-ali-sorted-RG-rmdup.bam -O hdfs://$hdfs_url/$sp_name-ali-sorted-RG-rmdup-realigned-recal.bam -R hdfs://$hdfs_url/$hg19 --known-sites hdfs://$hdfs_url/$dir_vcf/Mills_and_1000G_gold_standard.indels.hg19.sites.vcf  --known-sites hdfs://$hdfs_url/$dir_vcf/1000G_phase1.indels.hg19.sites.vcf  $spark_cmd


# GATK UnifiedGenotyper was removed from GATK 4.0 best practics
# GATK UnifiedGenotyper
#time bash -c "taskset -c 0-17  java -jar $dir_bin/GenomeAnalysisTK.jar -nt $cores -T UnifiedGenotyper -R $hg19  -L $bed  -metrics $dir_analyzed_sample/$sp_name-snps.metrics -stand_call_conf 10.0 -dcov 20000 -glm BOTH -I $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup-realigned-recal.bam -o $dir_analyzed_sample/$sp_name-Unified-SNP-INDLE.vcf"
#time java -jar $dir_bin/GenomeAnalysisTK.jar -nt $threads -T UnifiedGenotyper -R $hg19  -metrics $dir_analyzed_sample/$sp_name-snps.metrics -stand_call_conf 10.0 -stand_emit_conf 5.0 -dcov 20000 -glm BOTH -I $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup-realigned-recal.bam -o $dir_analyzed_sample/$sp_name-Unified-SNP-INDLE.vcf

#GARK HaplotypeCaller
date
gatk HaplotypeCallerSpark -I hdfs://$hdfs_url/$sp_name-ali-sorted-RG-rmdup-realigned-recal.bam -R hdfs://$hdfs_url/$hg19 -O hdfs://$hdfs_url/$sp_name-Haploy-SNP-INDLE.vcf -pairHMM AVX_LOGLESS_CACHING --maxReadsPerAlignmentStart 10 $spark_cmd
date
