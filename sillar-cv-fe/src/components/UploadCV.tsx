"use client";

import { useState } from "react";

export default function UploadCV() {
	const [file, setFile] = useState<File | null>(null);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [success, setSuccess] = useState(false);

	const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		const selectedFile = e.target.files?.[0];
		if (selectedFile) {
			if (selectedFile.type !== "application/pdf") {
				setError("Por favor, selecciona un archivo PDF");
				setFile(null);
				return;
			}
			setFile(selectedFile);
			setError(null);
		}
	};

	const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
		e.preventDefault();
		if (!file) {
			setError("Por favor, selecciona un archivo");
			return;
		}

		setLoading(true);
		setError(null);
		setSuccess(false);

		try {
			const response = await fetch(process.env.NEXT_PUBLIC_API_URL!, {
				method: "POST",
				headers: {
					"Content-Type": "application/pdf",
					"Content-Disposition": `attachment; filename="${file.name}"`,
				},
				body: file,
			});

			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(errorData.error || `Error: ${response.status}`);
			}

			setSuccess(true);
			setFile(null);
			// Reset the file input
			const form = e.target as HTMLFormElement;
			form.reset();
		} catch (err) {
			setError("Error al subir el archivo. Por favor, intenta nuevamente.");
			console.error("Upload error:", err);
		} finally {
			setLoading(false);
		}
	};

	return (
		<div className="max-w-xl mx-auto p-6">
			<form onSubmit={handleSubmit} className="space-y-6">
				<div className="space-y-2">
					<label
						htmlFor="cv-upload"
						className="block text-sm font-medium text-gray-700"
					>
						Sube tu CV (PDF)
					</label>
					<div className="mt-1">
						<div className="flex items-center justify-center w-full">
							<label
								htmlFor="cv-upload"
								className={`flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer
                  ${
										file
											? "border-green-500 bg-green-50"
											: "border-gray-300 bg-gray-50"
									}
                  hover:bg-gray-100 transition-colors duration-200`}
							>
								<div className="flex flex-col items-center justify-center pt-5 pb-6">
									<svg
										className={`w-8 h-8 mb-3 ${
											file ? "text-green-500" : "text-gray-500"
										}`}
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
										xmlns="http://www.w3.org/2000/svg"
									>
										<path
											strokeLinecap="round"
											strokeLinejoin="round"
											strokeWidth={2}
											d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
										/>
									</svg>
									<p className="mb-2 text-sm text-gray-500">
										{file
											? file.name
											: "Haz clic para subir o arrastra tu CV aquí"}
									</p>
									<p className="text-xs text-gray-500">Solo archivos PDF</p>
								</div>
								<input
									id="cv-upload"
									type="file"
									accept=".pdf"
									className="hidden"
									onChange={handleFileChange}
									disabled={loading}
								/>
							</label>
						</div>
					</div>
				</div>

				{error && (
					<div className="p-3 text-sm text-red-500 bg-red-50 rounded-md">
						{error}
					</div>
				)}

				{success && (
					<div className="p-3 text-sm text-green-500 bg-green-50 rounded-md">
						CV subido exitosamente. Te notificaremos por email cuando lo hayamos
						revisado.
					</div>
				)}

				<button
					type="submit"
					disabled={!file || loading}
					className={`w-full py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white
            ${
							!file || loading
								? "bg-gray-400 cursor-not-allowed"
								: "bg-blue-600 hover:bg-blue-700"
						} transition-colors duration-200`}
				>
					{loading ? "Subiendo..." : "Subir CV"}
				</button>
			</form>
		</div>
	);
}
