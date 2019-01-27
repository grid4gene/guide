#!/bin/bash

set -x
ulimit -n 102400

#input file
R1='TEST/FASTQ_LAURA/412_1.fastq.gz'
R2='TEST/FASTQ_LAURA/412_1.fastq.gz'
#reference file
hg19='reference/hg19.fasta'
dir_vcf='reference'
hw_threads=36
threads=3
cores=18
num_parallel=6
sp_name='pipe5'
dir_analyzed_sample='TEST/output'
dir_bin='/home/opt/tools'
bed='reference/Agilent_S06588914_Covered.chr.bed'



# Align the reads
time bash -c "${dir_bin}/bwa mem  -t $cores  $hg19  $R1 $R2 | ${dir_bin}/samtools view -@ $cores -Sb > $dir_analyzed_sample/$sp_name-bwa.bam"
# filter reads un-mapped reads and sort bam file
time bash -c " numactl -C 0-17 -m 0 ${dir_bin}/samtools view -@ $cores -b -h  -F 4 $dir_analyzed_sample/$sp_name-bwa.bam  > $dir_analyzed_sample/$sp_name-ali.bam"
# Sorting BAM
time bash -c " numactl -C 0-17 -m 0 ${dir_bin}/samtools sort -@ $cores $dir_analyzed_sample/$sp_name-ali.bam  -o $dir_analyzed_sample/$sp_name-ali-sorted.bam"

# index BAM
time bash -c "numactl  -C 0-17 -m 0 ${dir_bin}/samtools index -@ $cores $dir_analyzed_sample/$sp_name-ali-sorted.bam"


#split the bam file by the chromosome
#create a chromosome name list
#for i in {1..22} X Y M Un
for i in {1..22} X Y M
do
    chr=${chr}" "${i}
done
time chr_all=`${dir_bin}/samtools view -H $dir_analyzed_sample/$sp_name-ali-sorted.bam | awk -F"\t" '/@SQ/{print $2}' |  cut -d":" -f2 `

time parallel -j $cores "${dir_bin}/samtools view -h $dir_analyzed_sample/$sp_name-ali-sorted.bam {} | ${dir_bin}/samtools view -hbS - > $dir_analyzed_sample/$sp_name-ali-sorted.tmp.{}.bam" ::: $chr_all

export dir_bin
export sp_name
export dir_analyzed_sample
export chr
export chr_all
#Merge the bam file by the chromosome
merge_file(){    
        if [[ $1 != "Un" ]]
        then
            in_file="$dir_analyzed_sample/$sp_name-ali-sorted.tmp.chr$1.bam"
        else
            in_file=""
        fi
        out_file="$dir_analyzed_sample/$sp_name-ali.$1.bam"
        name="chr"$1"_"    

        for j in $chr_all
        do              
            if [[ "$j" == "$name"* ]]
            then
                in_file=$in_file" $dir_analyzed_sample/$sp_name-ali-sorted.tmp.$j.bam "                
            fi
        done

        #echo $1" and "$in_file
        if [[ $in_file == "$dir_analyzed_sample/$sp_name-ali-sorted.tmp.chr$1.bam" ]]
        then            
            mv -f "$dir_analyzed_sample/$sp_name-ali-sorted.tmp.chr$1.bam" "$dir_analyzed_sample/$sp_name-ali.$1.bam"
        else
            #echo "${dir_bin}/samtools merge -nf $out_file $in_file"
            ${dir_bin}/samtools merge -nf $out_file $in_file
        fi
}
export -f merge_file
time parallel -j $cores merge_file ::: $chr


#remove the tmp file
yes| rm -rf $dir_analyzed_sample/$sp_name-ali-sorted.tmp.*.bam

# Sorting BAM
time parallel -j $num_parallel "${dir_bin}/samtools sort -@ $threads $dir_analyzed_sample/$sp_name-ali.{}.bam  -o $dir_analyzed_sample/$sp_name-ali-sorted.{}.bam" ::: $chr

# Add ReadGroup
time parallel -j $cores "java -jar ${dir_bin}/picard.jar AddOrReplaceReadGroups  I=$dir_analyzed_sample/$sp_name-ali-sorted.{}.bam  O=$dir_analyzed_sample/$sp_name-ali-sorted-RG.{}.bam  RGSM=$sp_name RGLB=project RGPL=illumina RGID=none RGPU=none VALIDATION_STRINGENCY=LENIENT" ::: $chr

# Remove duplicates
time parallel -j $num_parallel "java -jar ${dir_bin}/picard.jar MarkDuplicates  REMOVE_DUPLICATES=TRUE CREATE_INDEX=TRUE VALIDATION_STRINGENCY=LENIENT MAX_RECORDS_IN_RAM=4000000 ASSUME_SORTED=TRUE I=$dir_analyzed_sample/$sp_name-ali-sorted-RG.{}.bam  O=$dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup.{}.bam  METRICS_FILE=$dir_analyzed_sample/$sp_name-pacard.{}.metrics" ::: $chr

# index BAM
time parallel -j $cores ${dir_bin}/samtools index $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup.{}.bam  ::: $chr


##############################################
#Note that indel realignment is no longer necessary for variant discovery if you plan to use a variant caller that performs a haplotype assembly step, such as HaplotypeCaller or MuTect2. However it is still required when using legacy callers such as UnifiedGenotyper or the original MuTect.
#https://software.broadinstitute.org/gatk/documentation/tooldocs/3.8-0/org_broadinstitute_gatk_tools_walkers_indels_RealignerTargetCreator.php
# RealignerTargetCreator
time parallel -j $num_parallel "java -jar $dir_bin/GenomeAnalysisTK.jar -nt $threads -T RealignerTargetCreator -known $dir_vcf/Mills_and_1000G_gold_standard.indels.hg19.sites.vcf  -known $dir_vcf/1000G_phase1.indels.hg19.sites.vcf  -R $hg19 -I $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup.{}.bam -o $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup.{}.bam.list"  :::$chr

##############################################
#This is not needed for the HaplotypeCaller
#https://software.broadinstitute.org/gatk/documentation/tooldocs/3.8-0/org_broadinstitute_gatk_tools_walkers_indels_IndelRealigner.php
#Note that indel realignment is no longer necessary for variant discovery if you plan to use a variant caller that performs a haplotype assembly step, such as HaplotypeCaller or MuTect2. However it is still required when using legacy callers such as UnifiedGenotyper or the original MuTect.
# IndelRealigner
time parallel -j $num_parallel "java -jar $dir_bin/GenomeAnalysisTK.jar  -T IndelRealigner -known $dir_vcf/Mills_and_1000G_gold_standard.indels.hg19.sites.vcf -known $dir_vcf/1000G_phase1.indels.hg19.sites.vcf -R $hg19 -I $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup.{}.bam -targetIntervals $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup.{}.bam.list -o $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup-realigned.{}.bam"  :::$chr


#BaseRecalibrator
time parallel -j $num_parallel "java -jar $dir_bin/GenomeAnalysisTK.jar  -nct $threads -T BaseRecalibrator -l INFO  -R $hg19   -knownSites $dir_vcf/Mills_and_1000G_gold_standard.indels.hg19.sites.vcf -knownSites $dir_vcf/1000G_phase1.indels.hg19.sites.vcf  -I  $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup-realigned.{}.bam -o  $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup-realigned.{}.grp" :::$chr

# GATK PrintReads
time parallel -j $num_parallel "java -jar $dir_bin/GenomeAnalysisTK.jar -nct $threads -T PrintReads -R $hg19 -I $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup-realigned.{}.bam -BQSR $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup-realigned.{}.grp -o $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup-realigned-recal-0.{}.bam" ::: $chr

# Filter mapping quality <10
time parallel -j $num_parallel "${dir_bin}/samtools view -@ $threads -h -q 10 $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup-realigned-recal-0.{}.bam |${dir_bin}/samtools view  -@ $threads -h -Sb > $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup-realigned-recal.{}.bam" ::: $chr

# index BAM
time parallel -j $cores  ${dir_bin}/samtools index $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup-realigned-recal.{}.bam :::$chr

# GATK UnifiedGenotyper
time parallel -j $num_parallel "java -jar $dir_bin/GenomeAnalysisTK.jar -nt $threads -T UnifiedGenotyper -R $hg19  -L $bed  -metrics $dir_analyzed_sample/$sp_name-snps.metrics -stand_call_conf 10.0 -dcov 20000 -glm BOTH -I $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup-realigned-recal.{}.bam -o $dir_analyzed_sample/$sp_name-Unified-SNP-INDLE.{}.vcf" ::: $chr

#GARK HaplotypeCaller
#time parallel -j $num_parallel "java -jar $dir_bin/GenomeAnalysisTK.jar -nct $threads -T HaplotypeCaller -L chr{} -R $hg19 -stand_call_conf 10.0 -minPruning 3  -mbq 5  -I $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup-realigned-recal.{}.bam -o $dir_analyzed_sample/$sp_name-Haploy-SNP-INDLE.{}.vcf" :::$chr
time parallel -j $num_parallel "java -jar $dir_bin/GenomeAnalysisTK.jar -nct $threads -T HaplotypeCaller -L $bed -R $hg19 -stand_call_conf 10.0 -minPruning 3  -mbq 5  -I $dir_analyzed_sample/$sp_name-ali-sorted-RG-rmdup-realigned-recal.{}.bam -o $dir_analyzed_sample/$sp_name-Haploy-SNP-INDLE.{}.vcf" ::: $chr
