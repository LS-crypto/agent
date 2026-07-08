/** 聊天图片附件：读取为 data URL 并校验大小/类型。 */

const MAX_IMAGES = 4;
const MAX_BYTES = 5 * 1024 * 1024;

const ALLOWED_MIMES = new Set([
  "image/jpeg",
  "image/png",
  "image/gif",
  "image/webp",
]);

const EXT_MIME: Record<string, string> = {
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
  ".gif": "image/gif",
  ".webp": "image/webp",
};

export interface ImageReadProgress {
  percent: number;
  currentFile: string;
  fileIndex: number;
  fileCount: number;
}

export function resolveImageMime(file: File): string | null {
  let type = (file.type || "").toLowerCase();
  if (type === "image/jpg" || type === "image/pjpeg") {
    type = "image/jpeg";
  }
  if (ALLOWED_MIMES.has(type)) return type;
  const dot = file.name.lastIndexOf(".");
  const ext = dot >= 0 ? file.name.slice(dot).toLowerCase() : "";
  return EXT_MIME[ext] ?? null;
}

function readOneFile(
  file: File,
  onFileProgress?: (percent: number) => void,
): Promise<string> {
  return new Promise((resolve, reject) => {
    if (file.size > MAX_BYTES) {
      reject(new Error(`「${file.name}」超过 5MB 限制`));
      return;
    }
    const reader = new FileReader();
    reader.onprogress = (e) => {
      if (!e.lengthComputable || !onFileProgress) return;
      onFileProgress(Math.min(100, Math.round((e.loaded / e.total) * 100)));
    };
    reader.onload = () => {
      if (typeof reader.result === "string") resolve(reader.result);
      else reject(new Error(`读取「${file.name}」失败`));
    };
    reader.onerror = () => reject(new Error(`读取「${file.name}」失败`));
    reader.readAsDataURL(file);
  });
}

/** 立即拷贝 FileList — input.files 是 live 对象，清空 value 后会变空。 */
export function snapshotFiles(files: FileList | File[] | null | undefined): File[] {
  return files ? Array.from(files) : [];
}

export async function readImageFiles(
  files: FileList | File[],
  existingCount = 0,
  onProgress?: (progress: ImageReadProgress) => void,
): Promise<string[]> {
  const picked = snapshotFiles(files);
  const list = picked.filter((f) => resolveImageMime(f) !== null);

  if (list.length === 0) {
    const names = picked.map((f) => f.name).join("、");
    throw new Error(
      picked.length
        ? `无法识别为图片（${names}）。支持 JPEG、PNG、GIF、WebP`
        : "未选择文件",
    );
  }
  if (existingCount + list.length > MAX_IMAGES) {
    throw new Error(`每条消息最多 ${MAX_IMAGES} 张图片`);
  }

  const urls: string[] = [];

  for (let index = 0; index < list.length; index += 1) {
    const file = list[index];
    onProgress?.({
      percent: Math.round((index / list.length) * 100),
      currentFile: file.name,
      fileIndex: index + 1,
      fileCount: list.length,
    });

    const url = await readOneFile(file, (pct) => {
      const base = (index / list.length) * 100;
      const slice = 100 / list.length;
      onProgress?.({
        percent: Math.min(99, Math.round(base + (pct / 100) * slice)),
        currentFile: file.name,
        fileIndex: index + 1,
        fileCount: list.length,
      });
    });
    urls.push(url);
  }

  onProgress?.({
    percent: 100,
    currentFile: list[list.length - 1]?.name ?? "",
    fileIndex: list.length,
    fileCount: list.length,
  });

  return urls;
}

export { MAX_IMAGES as CHAT_MAX_IMAGES };
